# PVPoolFiltration

La filtration de piscine consomme une énergie importante. Il est intéressant de la coupler à la production d’énergie photovoltaïque afin de diminuer son coût de fonctionnement.

Cette application est destinée à tourner sous `Appdaemon` dans `Home Assistant`.

Elle se distingue des autres applications de gestion de filtration de piscine déjà existantes par le fait qu’elle est pilotée par une application [PVOptimizer](https://github.com/loudemer/pvoptimizer)qui gère de manière globale les gros consommateurs d’énergie de la maison. 

Ce programme est adapté à un traitement de l’eau par oxygène actif (H2O2) que l’on peut désactiver si on ne désire pas l’utiliser.
## Mode de fonctionnement

Le traitement par oxygène actif nécessite plusieurs injections dans la journée en début de cycle de filtration. De ce fait, on effectue plusieurs cycles de filtration répartis au cours de la journée en tenant compte de l’ensoleillement.
La durée totale de filtration journalière est calculée selon un [abaque](https://github.com/scadinot/pool). 

Elle peut peut-être modulée par un coefficient de filtration pour tenir compte de la puissance de la pompe et du volume de la piscine.

Lorsque l’ensoleillement est insuffisant, le programme assure des petits cycles de filtration de 30 minutes avec injection d’oxygène actif. La durée de filtration restante est effectuée en heure creuse la nuit.

![Icon](https://github.com/loudemer/pvoptimizer/blob/main/images/applications.png?raw=true)
Il est possible de fonctionner en mode manuel si cela est nécessaire.
## Prérequis

1.	Switch de commande de la pompe de filtration
2.	Switch de commande de la pompe d’H2O2 (optionnel)
3.	Sonde de température de la piscine
## Installation

1.	Installation de l’add-on [appdaemon](https://appdaemon.readthedocs.io/en/latest/INSTALL.html) si besoin
2.	Installation de l’application [PVOptimizer](https://github.com/loudemer/pvoptimizer)
3.	Installation de l’application [PVPoolFiltration](https://github.com/loudemer/pvpoolfiltration)
4.	Mettre les fichiers `PVPoolFiltration.py` et `PVPoolFiltration.yaml` dans le répertoire `addon_configs/a0d7b954_appdaemon/apps`
5.	Mettre le fichier `piscine.yaml` dans le répertoire `/config/` de HA ou dans un sous répertoire dédié au fichiers yaml si vous en avez un.
## Configuration ##

1.	Ajouter dans le fichier `addon_configs/a0d7b954_appdaemon/appdaemon.yaml`
```yaml
       pvpoolfiltration_log 
         name: pvpoolfiltration_log
         filename: /homeassistant/log/ pvpoolfiltration.log
         log_generations: 3
         log_size: 100000 
```
Ceci vous permet de lire les log de l’application dans le fichier `/config/ pvpoolfiltration .log`
ou directement dans `http://ip_ha:5050`

2.	Compléter le fichier `PVPoolFiltration.yaml`
dans le répertoire`/addon_configs/a0d7b954_appdaemon/apps/` :

| attribut                | signification                                                                                   | exemple                                                 | commentaire                                                                                                                                                                           |
| ----------------------- |  ----------------------------------------------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|pompe_filtration|relai commande pompe de filtration |switch.pompe_filtration|requis, a compléter|
|temperature_eau|thermomètre piscine|sensor.temperature_eau|requis, a compléter|
|enable_solar_optimizer|activation de l'activation PVOptimizer|input_boolean.enable_solar_optimizer|déjà installé avec PVOptimizer|
|enable_solar_optimize_piscine|demande de cycle de filtration|input_boolean.device_request_x|x  = rang de déclaration dans la liste de PVOptimizer.yaml, déjà installé avec PVOptimizer|
|activation_cycle|activation du cycle par PVOptimizer|input_boolean.start_device_x|idem ci-dessus, déjà installé|
|coeff_filtration|Coefficient d'adapation à la puissance de la pompe|sinput_number.filtration_coeff_abaque|requis, présent dans piscine.yaml|
|duree_programmee|affichage de la duréee de filtration programée pour la journée|input_text.duree_filtration_programmee|requis, présent dans piscine.yaml|
|temp_max_piscine|temperature max de la piscine|input_number.temp_max_piscine|requis, présent dans piscine.yaml|
|duree_filtration_realisee|durée de filtration réalisée|sensor.duree_filtration_realisee|requis, présent dans piscine.yaml|
|nb_cycles_filtration|Nb de cycles de filtration réalisés|input_text.nb_cycles_filtration|requis, présent dans piscine.yaml|
|status_filtration|status pompe filtration|binary_sensor.piscine_status_pompe_filtration|optionel|
|heure_creuse|indicateur HP/HC|binary_sensor.rte_tempo_heures_creuses|requis, à compléter|
|manual_cycle|declenchement cycle manuel|input_boolean.start_manual_filtration|requis, présent dans piscine.yaml|
|mode_fonctionnement|Mode de filtration : Arrêt, manuel, automatique|input_select.mode_fonctionnement_filtration|requis, présent dans piscine.yaml|
|traitement_h2o2|traitement piscine par h2o2|oui / non|optionnel, à compléter par oui ou non|
|pompe_h2o2|relai commande pompe h2o2|switch.piscine_pompe_h2o2 ou none|optionnel, à compléter||h2o2_actif|traitement par h2o2 actif|input_boolean.prog_h2o2_actif ou none|optionnel, présent dans piscine.yaml, (a decocher)|
|duree_injection_h2o2|duree d'injection d'h2o2 dans la journée|input_number.duree_injection_h2o2 ou none|optionnel, présent dans piscine.yaml, (a decocher)|

Si vous n'utilisez pas le traitement par h2o2 mettez `non` pour `traitement_h2o2` et `none` pour `pompe_h2o2` et `duree_injection_h2o2`

3.	Recharger la configuration yaml dans outils/toute la configuration

## Le Dashboard ##

A titre d’exemple vous trouverez dans le dépôt un fichier `dasboard.yaml` à titre d’exemple de configuration de base tout à fait perfectible.

Il faut rajouter un sensor pour `input_boolean.automatisation_piscine` permettant d’activer  cette application.

## Mode d’emploi ##

Une fois l’installation réalisée, l’intégration est opérationnelle.

Vérifiez que vous avez bien activé les applications PVOptimizer et PVPoolFiltration.

Mettez le mode de filtration en `automatique`

Activer la demande de filtration dans PVOptimizer. Par la suite cette demande se remettra automatiquement en route tous les matins.

Vous pouvez faire une demande de cycle supplémentaire en cliquant sur le bouton `manuel`  

## Visualisation des problèmes éventuels ##

L’intégration génère un fichier de log qui est stocké dans le fichier `/config/log/pvpoolfiltration.log`.

Il est possible aussi d’avoir plus de détails en appelant directement la console de debug d’appdaemon : `http://<ip_homeassistant>:5050`.

Vous pouvez alors voir le démarrage et l’arrêt de l’intégration dans `main_log`, les erreurs éventuelles dans `error_log` et le déroulement de l’activité de l’intégration dans `pvpoolfiltration_log`.

## Désinstallation ##
Il faut retirer les 2 fichiers PVOptimizer.py et `PVPoolFiltration.yaml` dans le répertoire `addon_configs/a0d7b954_appdaemon/apps/`

Puis le fichier `piscine.yaml` dans le répertoire /config/ de HA,
Retirer aussi le dashboard PVPoolfiltration
Redémarrer HA.

