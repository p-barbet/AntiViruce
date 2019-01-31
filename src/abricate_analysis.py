#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os, sys, time
import argparse
import pandas as pd


def get_parser() :
	# Fonction permettant de pourvoir demander des arguments

	parser = argparse.ArgumentParser(description= \
		'Find ARM, virulence and toxin genes running ABRicate', \
			formatter_class=argparse.ArgumentDefaultsHelpFormatter)

	parser.add_argument('-f', action="store", dest='input', 
					type=str, required=True, help='tsv file with FASTA files paths and strains IDs (REQUIRED)')

	db_type = parser.add_mutually_exclusive_group(required=True)

	db_type.add_argument('--defaultdb', action="store", dest='defaultDatabase', \
						type=str, choices=['resfinder', 'card',	'argannot', 'ecoh', \
							'ecoli_vf', 'plasmidfinder', 'vfdb', 'ncbi', 'vir_clost', 'enterotox_staph', 'phages'], help='default \
								database to use (resfinder, card, argannot, ecoh, ecoli_vf, plasmidfinder, vfdb, ncbi. Incompatible with --privatedb)')

	db_type.add_argument('--privatedb', action="store", dest='privateDatabase', \
						type=str, help='private database name. Implies -dbp, -dbf. Incompatible with --defaultdb')

	parser.add_argument('-dbp', action="store", dest='privatedbPath', \
						type=str, help='path to abricate \
							databases repertory. Implies -dbf, --privatedb')	

	parser.add_argument('-dbf', action="store", dest='privatedbFasta', \
						type=str, help='Multifasta containing \
							the private database sequences. Implies -dbp, --privatedb')	

	parser.add_argument('-T', action="store", dest='nbThreads', 
					type=str, default=1, help='number of theard to use')

	parser.add_argument('-w', action="store", dest='workdir', 
		type=str, default='.', help='working directory')

	parser.add_argument('-r', action="store", dest='resdir', 
					type=str, default='abricateResults', help='results directory name')

	parser.add_argument('--mincov', action="store", dest='mincov', \
						type=str, default='80', help='Minimum proportion of gene covered')

	parser.add_argument('--minid', action="store", dest='minid', \
						type=str, default='90', help='Minimum proportion of exact nucleotide matches')

	parser.add_argument('-o', action="store", dest='outputFile', \
						type=str, default='ABRicate_files.tsv', help='output file name')

	return parser

# Objet génome (atributs : ID, fichier fasta, fichier abricate)
class genome(object) :

	def __init__(self) :
		self.ID = ""
		self.fastaFile = ""
		self.abricateFile = ""

	def setID(self, ID) :
		self.ID = ID

	def setFastaFile(self, fastaFile) :
		self.fastaFile = fastaFile

	def setAbricateFile(self, abricateFile) :
		self.abricateFile = abricateFile


# Fonction qui crée tous les objets génomes et les stock dans un dictionnaire avec les IDs de ces derniers comme clés
def getGenomesObjects(inputFile, dicoGenomes) :
	data = open(inputFile, 'r')
	lines = data.readlines() 
	data.close()

	for line in lines :

		line = line.rstrip() # retire les retours chariot des lignes
		infos = line.split("\t")

		ID = infos[1] # ids des génomes
		fastaFile = infos[0] # chemins des assemblages

		dicoGenomes[ID] = genome() 

		dicoGenomes[ID].setID(ID) 
		dicoGenomes[ID].setFastaFile(fastaFile)
		

# Fonction qui crée la nouvelle base de donée abricate
def setupPrivatedb(dbName, abricateDbsRepertory, dbMultifasta) :

	multifastaName = dbMultifasta.split("/")[-1] # nom du fichier multifasta de la base a créer

	if abricateDbsRepertory[-1] != '/' :
		abricateDbsRepertory += '/'

	if not os.path.exists(abricateDbsRepertory + dbName) : # création du répertoire de la base dans abricate si il n'existe pas
		os.system("mkdir " + abricateDbsRepertory + dbName) 
	else : 
		sys.exit("ERREUR: La base de donnée " + dbName + " existe déjà")

	os.system("cp " + dbMultifasta + " " + abricateDbsRepertory + dbName) # copie du multifasta dans le répartoire abricate

	os.system("mv " + abricateDbsRepertory + dbName + "/" + multifastaName + " " + abricateDbsRepertory + dbName + "/" +"sequences") # renommage du multifasta en "sequences"

	os.system("abricate --setupdb") # idexation de la base dans abricate


# Fonction qui lance ABRicate pour chaque genome (par défaut mincov = 80 et minid = 90)
def runABRicate(dicoGenomes, dbName, mincov, minid, analysisDirectory, nbThreads) :

	for genome in dicoGenomes :

		abricateResult = analysisDirectory + "ABRicate_" + dicoGenomes[genome].ID + "_" + dbName + ".tsv" # nom du fichier résultat de l'analyse
		os.system("abricate " + dicoGenomes[genome].fastaFile + " --db " + dbName + " --mincov " + mincov + " --minid " + minid + " --threads " + str(nbThreads) + " > " + abricateResult) # lancement d'ABRicate

		dfResult = pd.read_csv(abricateResult, sep='\t', index_col=0, dtype = str) # lecture du fichier résultat avec pandas (dataframe)

		rowsNames = [dicoGenomes[genome].ID]*len(dfResult.index) # liste contenant autant de fois l'ID de la souche qu'il n'y a de ligne dans le fichier
		dfResult.index = rowsNames # renomage de chaque ligne par l'ID du génome
		dfResult.index.name = "#FILE" # nom de l'index

		dfResult.to_csv(abricateResult, sep='\t') # Récriture du fichier

		dicoGenomes[genome].setAbricateFile(abricateResult)


# Fonction qui crée un fichier contenant les chemin des fichiers résultats et les IDs des génomes
def getABRicateFilesList(resultsDirectory, dicoGenomes, outputFile) :


	abricateList = open(resultsDirectory + outputFile, 'w') 

	for genome in dicoGenomes :
		resultFile = dicoGenomes[genome].abricateFile
		ID = dicoGenomes[genome].ID
		abricateList.write(resultFile + '\t' + ID + '\n') 

	abricateList.close()


# Fonction qu supprime la base de donnée privée
def uninstall_private_db(dbName, abricateDbsRepertory) :

	if abricateDbsRepertory[-1] != '/' :
		abricateDbsRepertory += '/'
	
	os.system("rm -R " + abricateDbsRepertory + dbName)

	os.system("abricate --setupdb")

	
def main():
	
	##################### gets arguments #####################

	parser=get_parser()
	
	#print parser.help if no arguments
	if len(sys.argv)==1:
		parser.print_help()
		sys.exit(1)
	
	# mettre tout les arguments dans la variable Argument
	Arguments=parser.parse_args()

	if Arguments.privateDatabase is not None and (Arguments.privatedbPath is None or Arguments.privatedbFasta is None) : # Vérification que les arguments -dbp et-dbf sont bien présents si la base de donées choisie est privée
		 parser.error("--privatedb argument requires -dbp and -dbf.")

	if Arguments.defaultDatabase is not None and (Arguments.privatedbPath is not None or Arguments.privatedbFasta is not None) : # Vérification que les arguments -dbp et-dbf en cas de base de données par défaut
		 parser.error("--defaultdb argument not requires -dbp and -dbf.")

	begin = time.time()

	WORKDIR = Arguments.workdir
	RESDIR = Arguments.resdir
	if WORKDIR[-1] != '/' :
		WORKDIR += '/'

	if RESDIR[-1] != '/' : 
		RESDIR += '/'


	if not os.path.exists(WORKDIR + RESDIR) :
		os.system('mkdir ' + WORKDIR + RESDIR) 
		os.system('mkdir ' + WORKDIR + RESDIR + 'analysis/')

	DIR = WORKDIR + RESDIR
	analysisDirectory = WORKDIR + RESDIR + "analysis/" 

	dicoGenomes = {}
	
	getGenomesObjects(Arguments.input, dicoGenomes) # Construction des objets génomes



	if Arguments.privateDatabase is not None : # si base de données privée

		DATABASE_NAME = Arguments.privateDatabase
		setupPrivatedb(DATABASE_NAME, Arguments.privatedbPath, Arguments.privatedbFasta) # 
		

	else : # si base de données par défaut
		DATABASE_NAME = Arguments.defaultDatabase


	beginAbricate = time.time()

	runABRicate(dicoGenomes, DATABASE_NAME, Arguments.mincov, Arguments.minid, analysisDirectory, Arguments.nbThreads) # lance Abricate pour tous les génomes

	endAbricate = time.time()

	getABRicateFilesList(DIR, dicoGenomes, Arguments.outputFile) # création du fichier avec les chemins des fichiers résultats et les IDs des génomes 

	
	if Arguments.privateDatabase is not None : # si base de données privée

		uninstall_private_db(Arguments.privateDatabase, Arguments.privatedbPath)

	end = time.time()

	abricateTime = endAbricate - beginAbricate

	print("\n")
	print("Temps d'exécution d'ABRicate par souche : " + str(round(abricateTime/len(dicoGenomes),3)))

	print ("Temps d'exécution de l'analyse ABRicate : " + str(round(end - begin,3)) + " secondes")

# lancer la fonction main()  au lancement du script
if __name__ == "__main__":
	main()	            		           		

