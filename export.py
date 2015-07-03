#!/usr/bin/python
# -*-coding:Utf-8 -*

try:
  from subprocess import Popen, PIPE
  #import csv, os, argparse, smtplib, socket
  import csv, os, argparse, socket
  from ftplib import FTP
  import logging
  #from logging.handlers import RotatingFileHandler
  from logging.handlers import SMTPHandler
  from logging.handlers import TimedRotatingFileHandler
except ImportError:
  print ("Fail to load all module. You need to install modules: argparse, ")

###############################################################################
#### Parsage des arguments
###############################################################################

parser = argparse.ArgumentParser(description='')
parser.add_argument("-c", "--csv", dest="file_csv", help='Csv file to load', default="./exemple.csv")
parser.add_argument("-d", "--dest", dest="dest_dir", help='Directory to write zip', default="./")
parser.add_argument("-s", "--src", dest="src_dir", help='Directory where are directory to compress', default="./")
parser.add_argument("-v", "--verbose", dest="log", help='Print log on console', action='store_true')
args = parser.parse_args()

file_csv = args.file_csv
dest_dir = args.dest_dir
src_dir = args.src_dir
print_log = args.log

###############################################################################
######## Declaration des variables mail

mail = {}
mail['Server'] = 'smtp.mydomain.me'
mail['From'] = socket.gethostname() + '@mydomain'
mail['To'] = 'other@mydomain','me@mydomain'
mail['Subject'] = 'Trouble in the force'

###############################################################################
### Paramétres d'enregistrement des logs

# création de l'objet logger qui va nous servir à écrire dans les logs
logger = logging.getLogger()

# on met le niveau du logger à DEBUG, comme ça il écrit tout
logger.setLevel(logging.DEBUG)

# création d'un formateur qui va ajouter le temps, le niveau
# de chaque message quand on écrira un message dans le log
formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')

# création d'un formateur pour les mails utilisateurs
formatter2 = logging.Formatter('Date: %(asctime)s \nLevel: %(levelname)s \nMessage: %(message)s')

## On ajoute un handler qui va gérer l'envoi de mails.
smtp_handler = SMTPHandler(mail['Server'], mail['From'], mail['To'], mail['Subject'], credentials=None)
# On définie le niveau des logs à ERROR pour que les utilisateurs ne recoivent pas les messages de niveaux inférieure (INFO)
smtp_handler.setLevel(logging.ERROR)
# On utilise le format formatter2 pour la rédaction des mails.
smtp_handler.setFormatter(formatter2)
# On ajoute notre handler au logger
logger.addHandler(smtp_handler)

"""
# création d'un handler qui va rediriger une écriture du log vers
# un fichier en mode 'append', avec 1 backup et une taille max de 1Mo
file_handler = RotatingFileHandler('./export_app.log', 'a', 10000000, 1)

# on lui met le niveau sur DEBUG, on lui dit qu'il doit utiliser le formateur
# créé précédement et on ajoute ce handler au logger
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
"""

## création d'un second handler qui va rediriger chaque écriture de log
## sur la console si l'option verbose est active
if print_log is True:
  steam_handler = logging.StreamHandler()
  # On place le niveau de log à DEBUG pour que tout soit écrit dans le fichier log
  steam_handler.setLevel(logging.DEBUG)
  # On utilise le schéma 'formatter' pour le format d'écriture dans les logs
  steam_handler.setFormatter(formatter)
  # On ajoute steam_handler à logger
  logger.addHandler(steam_handler)
  print("\nVerbose mode activated\n")

## On ajoute un troisieme handler qui va gérer la rotation des logs par jours avec un historique de 30 jours.
rotate_handler = TimedRotatingFileHandler('./export_app.log', when='D', interval=1, backupCount=30)
# On place le niveau de log à DEBUG pour que tout soit écrit dans le fichier log
rotate_handler.setLevel(logging.DEBUG)
# On utilise le schéma 'formatter' pour le format d'écriture dans les logs
rotate_handler.setFormatter(formatter)
# On ajoute steam_handler à logger
logger.addHandler(rotate_handler)

### Fonctionnement des handlers
"""
  Pour écrire dans le fichier de log sans que les utilisateurs ne recoivent de mails, nous utiliseront les fonctions:
  logger.info() pour écrire dans le fichier log une entrée de type INFO
  logger.warning(), une entrée de type WARNING

  Pour écrire dans le fichier log, et que les utilisateurs reçoivent un mail, nous utiliseront les fonctions:
  logger.error()
  logger.critical()

"""

###############################################################################
# Fonction de parsage du fichier csv
###############################################################################

def open_csv(file_csv):
  export_entry = {}
  # On vérifie que le fichier csv existe.
  try:
    test_csv = open(file_csv, 'r')
    logger.info("I load %s as csv file", file_csv)
    with open(file_csv) as csvfile:
      # Le fichier cvs est lue si il est présent, et on l'enregistre dans un dictionnaire avec la premiére ligne correspondant aux clés du dict, et les entrées suivante comme ces valeurs correspondante. Donc nos clé pour ce dict sera le nom des répertoires à compressé.
      export_reader = csv.DictReader(csvfile, delimiter=';')
      for row in export_reader:
        zip_dir = src_dir + row['FTP']
        # Pour chaque entrée de répertoire trouver dans le fichier csv, on vérifie que le répertoire existe
        if os.path.exists(zip_dir) is True:
          if row['FTP'] not in export_entry:
            export_entry[row['FTP']] = {}  
          export_entry[row['FTP']]['login'] = row['login']
          export_entry[row['FTP']]['pwd'] = row['pwd']
          export_entry[row['FTP']]['dst'] = row['destination'].split(",")
        else:
          # Si le répertoire n'existe pas, nous envoyons une erreur level ERROR
          logger.error('No folder %s found in directory %s. Corresponding csv entry: %s;%s;%s;%s', row['FTP'], src_dir , row['FTP'], row['login'], row['pwd'], row['destination'])
#          logger.critical('No folder found. Maybe a wrong entry in %s ?. Corresponding entry: %s' , file_csv, row )
  except IOError:
    # Si le fichier n'existe pas, nous alertons les utilisateurs et inscrivont l'erreur dans le fichier log
    logger.critical('No %s founded', file_csv)
  return(export_entry)

###############################################################################
### Fonction de compression des dossiers
###############################################################################

def compress_dir(export_entry, src_dir, dest_dir):
  for key,value in export_entry.items():
    zip_dir = src_dir + key
    zip_path = dest_dir + key + ".zip"
    zip_file = key + ".zip"
    # On vérifie que le répertoire de destination existe
    if os.path.exists(zip_dir) is True:
      # On appele zip pour compréssé les dossiers.
      cmd_zip = Popen(['/usr/bin/zip', '-q', '-P', export_entry[key]["pwd"], '-r', zip_path, zip_dir],    stdout=PIPE, stderr=PIPE)
      # On stock la sortie standard et la sortie d'erreur
      stdout, stderr = cmd_zip.communicate()
      # Si la sortie std existe, on la log
      if len(stdout) > 0:
        logger.warning(stdout)
      # On enregistre le nom du fichier compréssé et son chemin
      export_entry[key]['zip'] = zip_file
      export_entry[key]['ZipPath'] = zip_path
    else:
      # Si le répertoire de destination n'existe pas, on log l'erreur
      logger.error("I Can't find directory %s" , zip_dir)
  return(stdout, zip_dir, zip_path, zip_file, export_entry)

###############################################################################
### Fonction d'export via ftp
###############################################################################

def send2ftp(zip_dir, zip_path, export_entry, zip_file):
  logs = {}
  for key,values in export_entry.items():
    #logger.info("Host: %s, Value: %s.", key, values)
    user = export_entry[key]['login']
    password = export_entry[key]['pwd']
    file = export_entry[key]['zip']
    temp_file = export_entry[key]['zip'] + ".tmp"
    backup_file = "Backup_" + export_entry[key]['zip']
    for host in export_entry[key]['dst']:
      if host not in logs:
        logs[host] = {}
        logs[host]['log'] = []
      #  logs[host]['attemps'] = 0
      logs[host]['attemps'] = 0
      while logs[host]['attemps'] < 2:
        logs[host]['attemps'] += 1
        logger.info("Attemp number %s for file %s on host %s" , logs[host]['attemps'], file, host)
        # D'abord on vérifie que l'on peut établir un connexion ftp avec l'hote de destination
        try:
          ftp = FTP(host, user, password, timeout=10)
          # Si on peut établir la connexion, on continue :)
          try:
            # On essaye de créer le dossier apphs, si cela échoue, on s'en fout
            ftp.mkd("apphs")
          except Exception,fail_mkdir:
            #logger.info(fail_mkdir)
            pass
          # On essaye de transférer les fichiers
          try:
            # On rentre dans le répertoire apphs
            ftp.sendcmd( 'CWD apphs')
            # On liste les fichiers
            files_list = ftp.nlst()
            #Si un fichier .tmp est présent, on le supprime
            if temp_file in files_list:
              ftp.delete(temp_file) 
            # On ouvre le fichier zip à envoyé
            f = open(export_entry[key]['ZipPath'], 'rb')
            # On l'envoi en tant que fichier .tmp
            ftp.storbinary('STOR ' + temp_file, f)
            # Si un fichier de backup existe, on le supprime
            if backup_file in files_list:
              ftp.delete(backup_file)
            # On renome le fichier zip existant en backup_
            ftp.rename(file, backup_file)
            # On renome le fichier temporaire
            ftp.rename(temp_file, file)
            # On valide la transaction pour sortir de la boucle
            logs[host]['attemps'] = 3
            # On logs
            logger.info("I have sent file %s to host %s" , file, host)
            # On ferme la session ftp
            ftp.close()
            # On ferme le fichier
            f.close()
          except Exception,fail_sent:
            # Si le nombre d'essai est inférieure à 2, on log un warning, sinon on log une ERROR
            if logs[host]['attemps'] == 2:
              logger.error("Fail to sent file '%s' to host '%s'. Attemp number %s, Message : %s", file, host, logs[host]['attemps'], fail_sent )
            if logs[host]['attemps'] < 2:
              logger.warning("Fail to sent file '%s' to host '%s'. Attemp number %s, Message : %s", file, host, logs[host]['attemps'], fail_sent )
        except Exception,fail_con:
          # Si le nombre d'essai est inférieure à 2, on log un warning, sinon on log une ERROR
          if logs[host]['attemps'] == 2:
            logger.error("Fail to connect to host '%s' with user '%s'. Attemp number %s, Message : %s", host, user, logs[host]['attemps'], fail_con)
          if logs[host]['attemps'] < 2:
            logger.warning("Fail to connect to host '%s' with user '%s'. Attemp number %s, Message : %s", host, user, logs[host]['attemps'], fail_con)

export_entry = open_csv(file_csv)

stdout, zip_dir, zip_path, zip_file, export_entry = compress_dir(export_entry, src_dir, dest_dir)

send2ftp(zip_dir, zip_path, export_entry, zip_file)

