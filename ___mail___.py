import smtplib

from email.mime.text import MIMEText

from email.mime.multipart import MIMEMultipart
    
# Informations de connexion et de l'expéditeur
sender_email = "serveur.mission.geii@gmail.com"
receiver_email = "warren.privat@u-bordeaux.fr"
#receiver_email = "warren.privat@u-bordeaux.fr"
# Configuration du message

id_mission= "0012561651"
nom= "privat"
prenom= "warren"
date_demande= "13/03/2025"
nom_mission= "Test1234"

date_depart= "01/01/1900"
heure_depart= "00:15"

date_retour= "01/01/1900"
heure_retour= "00:15"

adresse= "1 trou de "
ville= "MonQ"
code_postal= "69690"
pays= "La FRANCEEEEEEEE"
frais= "BG"
transport= "navette spacial"
hotel= "OUI"
ptdej= "OUI"

subject = f"Nouvelle demande de mission de {nom}"
body=f"""
<div>Hey, Valérie <br><br>Une nouvelle demande de mission: 
<a href="http://geii.iut.u-bordeaux.fr/mission/view_mission/{id_mission}" target="_blank" rel="noopener" data-mce-href="http://geii.iut.u-bordeaux.fr/mission/view_mission/{id_mission}" data-mce-selected="inline-boundary">{id_mission} </a><br></div><div><br data-mce-bogus=3D"1"></div>
<div>Demandeur: {nom} {prenom} le {date_demande}<br data-mce-bogus=3D"1"></div>
<div>Intitulé de mission: {nom_mission}<br data-mce-bogus=3D"1"></div>
<div>Date de départ: le {date_depart} {heure_depart}<br data-mce-bogus=3D"1"></div><div>Date de retour: le {date_retour} {heure_retour}</div>
<div>Lieu du déplacement: {adresse} {ville} {code_postal} {pays}<br data-mce-bogus=3D"1"></div>
<div>Frais ? : {frais}<br data-mce-bogus=3D"1"></div>
<div>Moyen de Transport: {transport}<br data-mce-bogus=3D"1"></div>
<div>Hôtel?: {hotel}</div>
<div>Petit déjeuner: {ptdej}<br data-mce-bogus=3D"1"></div><div><br data-mce-bogus=3D"1"></div>
<div>@+<br data-mce-bogus=3D"1"></div>"""

    # Création de l'objet message
message = MIMEMultipart()
message["From"] = sender_email
message["To"] = receiver_email
message["Subject"] = subject
# Ajout du corps de texte
message.attach(MIMEText(body, "html"))
try:
    with smtplib.SMTP("smtpauth.u-bordeaux.fr", 587) as server:
        server.starttls()  # Sécurise la connexion
        server.sendmail(sender_email, receiver_email, message.as_string())
        #print("Email envoyé avec succès")
except Exception as e:
    #print(f"Erreur lors de l'envoi de l'email : {e}")
    e=0