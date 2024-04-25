#############################################################################################################
# PoolFiltration application for appdaemon (Home Assistant)
# Author : Gerard Mamelle (2024)
# Version : 1.0.2
# Program under MIT licence
#
# This program must be used with an energy optimizer application like PVOptimizer 
# FILTRATION PROTOCOL:
# Day filtration duration is computed on water temperature 
# Adjusted with coefficient depending of power filtration pump
# During the day he tries to perform 1 hour filtration cycle (depending on solar available power)
# Then he stops at least 1 hour before next filtration cycle
# Filtration stops when computed filtration time duration is reached
# At the end of the day, if filtration time duration is not reached, filtration is done during 
# peak_off hours at night
# Water treatment is performed at the beginning of each filtration cycle with an injection of h2o2 
############################################################################################################
# TRAITEMENT H2O2
# Debit pompe 65 ml/mn
# Dose pour 45 m3 
# Moins de 25° : 240 ml / J    environ 240 Sec 
# Plus de 25° : 430 ml / J  environ 430 Sec mn
##############################################################################################
import hassapi as hass
import math
import datetime
from datetime import timedelta

DEFAULT_FILTRATION_COEFF = 0.6
DEFAULT_WATER_TEMP = 15.0 
INTERVAL_CYCLE  = 60*60      # interval minimum entre 2 cycles en secondes         

# Programme principal
class PoolFiltration(hass.Hass):

    def initialize(self):
        self.use_h2o2 = bool(self.args['traitement_h2o2'] == 'oui')
        self.temperature_eau = self.get_temperature_eau()
        self.temp_max_eau = self.get_temp_max_eau()
        self.heure_creuse = self.get_heure_creuse()
        self.coeff_filtration = self.get_coeff_filtration()
        self.duree_realisee = self.get_duree_realisee()
        self.duree_injection_h2o2 = self.get_duree_injection_h2o2()
        self.duree_journaliere_injection_h2o2 = 240
        self.temps_filtration = timedelta(minutes = 0)
        self.mode_fonctionnement = self.get_state(self.args['mode_fonctionnement'])
        if self.use_h2o2:
            self.h2o2_actif = self.get_state(self.args['h2o2_actif'])
        self.nb_cycle = 0
        
        self.check_temperature(None)
        self.compute_duree_abaque()

        # Init listen for pool events
        self.listen_state(self.change_coeff_filtration,self.args["coeff_filtration"])        
        self.listen_state(self.start_cycle_optimizer,self.args["activation_cycle"]) 
        self.listen_state(self.start_manual_cycle,self.args["manual_cycle"])        
        self.listen_state(self.change_heure_creuse,self.args["heure_creuse"]) 
        self.listen_state(self.change_mode_fonctionnement,self.args["mode_fonctionnement"]) 
        if self.use_h2o2:
            self.listen_state(self.change_h2o2_actif,self.args["h2o2_actif"]) 
            self.listen_state(self.change_duree_injection_h2o2,self.args["duree_injection_h2o2"]) 
         
         # Planification de la journée
        self.run_daily(self.init_day,"05:00:00")  
        self.run_at_sunrise(self.send_enable_filtration, offset=timedelta(minutes=10).total_seconds())                       
        self.run_daily(self.check_water_treatment, "11:00:00" , cycle = 1)
        self.run_daily(self.check_water_treatment, "15:00:00" , cycle = 2)

        self.log('Initialisation Module Filtration Piscine OK')
    
    def get_temp_max_eau(self) -> float:
        try:
            return float(self.get_safe_float("temp_max_piscine"))
        except Exception as e:
            self.log("Error getting max temp, using default of 15.0", e)
            return DEFAULT_WATER_TEMP
    
    def get_heure_creuse(self) -> str:
        try:
            return self.get_state(self.args["heure_creuse"]) 
        except Exception as e:
            self.log("Error getting heure creuse, using default off", e)
            return 'off'

    def get_temperature_eau(self) -> float:
        try:
            return float(self.get_safe_float("temperature_eau"))
        except Exception as e:
            self.log("Error getting water temp, using default of 15.0", e)
            return 20.0

    def get_coeff_filtration(self) -> float:
        try:
            coeff = float(self.get_safe_float("coeff_filtration"))
        except Exception as e:
            self.log("Error getting filtration coeff, using default of 0.6", e)
            return DEFAULT_FILTRATION_COEFF
        return coeff / 100.0
     
    # return filtration duration in minutes
    def get_duree_realisee(self) -> timedelta:
        try:
            fduree_realisee = float(self.get_safe_float("duree_filtration_realisee"))*60.0
        except Exception as e:
            self.log("Error getting filtration duration, using default of last value", e)
            return self.duree_realisee
        return timedelta(minutes = int(fduree_realisee))
    
    # return h2o2 injection duration in seconds
    def get_duree_injection_h2o2(self) -> int:
        if self.use_h2o2:
            try:
                fduree_injection = float(self.get_safe_float("duree_injection_h2o2"))
            except Exception as e:
                self.log("Error getting h2o2 injection duration, using default of 60", e)
                return 60
            return int(fduree_injection)
        else:
            return 0
    
    # Get a safe float state value for an entity.
    # Return None if entity is not available
    def get_safe_float(self, entity_id: str):
        state = self.get_state(self.args[entity_id])
        if not state or state == "unknown" or state == "unavailable":
            return None
        float_val = float(state)
        return None if math.isinf(float_val) or not math.isfinite(float_val) else float_val

    # Initialisation de la journee
    def init_day(self, kwargs):
        self.log("Initialisation de la journee")
        self.compute_duree_abaque()
        # reinitialisation de la temperature max de l'eau
        self.set_value(self.args["temp_max_piscine"], DEFAULT_WATER_TEMP)
        self.nb_cycle = 0
        self.set_value(self.args['nb_cycles_filtration'], str(self.nb_cycle))
    
    # changement HP / HC
    def change_heure_creuse(self, entity, attribute, old_state, new_state, kwargs):
        self.heure_creuse= new_state
        if self.heure_creuse == 'on' and self.mode_fonctionnement == 'automatique':
            # Filtration de fin de journée en heure creuse
            duree_restante = int(self.temps_filtration.total_seconds() - self.duree_realisee.total_seconds())
            if duree_restante > 0:
                self.log('Filtration HC demarree')
                self.start_pompe_filtration()
                if self.use_h2o2:
                    duree_realisee_h2o2 = self.get_duree_injection_h2o2()
                    duree_restante_h2o2 = self.duree_journaliere_injection_h2o2 - duree_realisee_h2o2
                    if duree_restante_h2o2 > 0:
                        self.inject_h2o2(duree_restante_h2o2) 
                self.run_in(self.stop_auto,duree_restante)          

    # Changement du mode de fonctionnement
    def change_mode_fonctionnement(self, entity, attribute, old_state, new_state, kwargs):
        self.mode_fonctionnement = new_state
        if self.mode_fonctionnement == 'arret':
            self.set_state(self.args["enable_solar_optimize_piscine"],state='off')
            self.stop_pompe_filtration()
        if self.mode_fonctionnement == 'automatique':
            self.set_state(self.args["enable_solar_optimize_piscine"],state='on')
        if self.mode_fonctionnement == 'manuel':
            self.set_state(self.args["enable_solar_optimize_piscine"],state='off')
    
    # Changement du status traitement par H2O2
    def change_h2o2_actif(self, entity, attribute, old_state, new_state, kwargs):
        self.h2o2_actif = new_state

    # Changement de la duree d'injection d'H2O2
    def change_duree_injection_h2o2(self, entity, attribute, old_state, new_state, kwargs):
        self.duree_injection_h2o2 = self.get_duree_injection_h2o2()

    # Demarrage d'un cycle manuel de 1 h
    def start_manual_cycle(self, entity, attribute, old_state, new_state, kwargs):
        if new_state == "on" and self.mode_fonctionnement != 'arret':
            self.log('Demarrage cycle manuel')
            self.run_manual_cycle()
        else:
            self.stop_manual(None)
    
    # activation cycle manuel pendat 1h
    def run_manual_cycle(self):
        self.set_state(self.args['mode_fonctionnement'], state='manuel')
        self.start_pompe_filtration()
        self.inject_h2o2(self.get_duree_injection_h2o2()) 
        self.nb_cycle = self.nb_cycle + 1
        self.value(self.args['nb_cycles_filtration'], str(self.nb_cycle))
        self.run_in(self.stop_manual, 60*60)

    # Demarrage ou arret d'un cycle commandee par l'optimizer (activation cycle)
    def start_cycle_optimizer(self, entity, attribute, old_state, new_state, kwargs):
        if self.mode_fonctionnement != 'automatique':
            return
        self.log(f'Commande cycle optimizer = {new_state}')
        self.duree_realisee = self.get_duree_realisee()
        if new_state == 'on' and  self.heure_creuse == 'off' and self.duree_realisee < self.temps_filtration:
            self.log('Filtration HP demarree')
            self.start_pompe_filtration()
            if self.use_h2o2:
                self.inject_h2o2(self.get_duree_injection_h2o2()) 
            self.nb_cycle = self.nb_cycle + 1
            self.set_value(self.args['nb_cycles_filtration'], str(self.nb_cycle))
        else:
            self.log('Filtration arretee par l optimizer')
            self.stop_pompe_filtration()
            if (self.duree_realisee < self.temps_filtration):
                self.run_in(self.send_enable_filtration, INTERVAL_CYCLE)

    # Envoi une demande filtration à l'Optimizer
    def send_enable_filtration(self, kwargs):
        self.set_state(self.args["enable_solar_optimize_piscine"],state='on')

    # Modification de la temperature, on enregistre et on reajuste la temperature max si besoin
    # La temperature est prise 10 mn apres le debut d'une filtration
    def check_temperature(self, kwargs):
        if self.get_state(self.args["constrain_input_boolean"]) == 'off':
            return
        self.temperature_eau = self.get_temperature_eau()
        self.temp_max_eau = self.get_temp_max_eau()
        self.log(f'temp eau ={self.temperature_eau}')
        if self.temperature_eau > self.temp_max_eau :
            self.temp_max_eau = self.temperature_eau
            self.set_value(self.args["temp_max_piscine"], self.temp_max_eau)
            self.compute_duree_abaque()
    
    # Verifie si le traitement minimum h2o2 est effectue (pas de soleil)
    def check_water_treatment(self, kwargs):
        min_cycle = int(kwargs['cycle'])
        if min_cycle > self.nb_cycle and self.get_state(self.args['pompe_filtration']) == 'off':
            self.start_pompe_filtration()
            if self.use_h2o2:
                self.inject_h2o2(self.get_duree_injection_h2o2()) 
            self.nb_cycle = self.nb_cycle + 1
            self.run_in(self.stop_auto, 30*60)
        
    # Modification du coefficient de temps de filtration
    def change_coeff_filtration(self, entity, attribute, old, new, kwargs):
        self.log('Appel traitement changement Coefficient')
        self.compute_duree_abaque()

    # Sequence injection h2o2 au debut du cycle de filtration
    def inject_h2o2(self, duree: int):
        self.run_in(self.check_temperature, 5)
        if self.h2o2_actif == 'off' or not self.use_h2o2:
            return
        self.log("Inject H2O2")
        self.start_pompe_h2o2() 
        self.run_in(self.stop_pompe_h2o2,  duree)
        self.run_in(self.stop_pompe_h2o2,  duree + 10)

    # Arret pompe H2O2 
    def stop_pompe_h2o2(self, kwargs):
        if self.h2o2_actif == 'off' or not self.use_h2o2:
            return
        if self.get_state(self.args['pompe_h2o2']) == 'on':
            self.turn_off(self.args['pompe_h2o2'])
            self.log("Pompe h2o2 OFF")
        
    # Demarrage pompe H2O2 
    def start_pompe_h2o2(self):
        if self.h2o2_actif == 'off' or not self.use_h2o2:
            return
        self.turn_on(self.args['pompe_h2o2'])
        self.log("Pompe h2o2 ON")
    
    # demarrage pompe filtration
    def start_pompe_filtration(self):
        self.turn_on(self.args['pompe_filtration'])
        self.log("Pompe filtration ON")
        
    # arret pompe filtration
    def stop_pompe_filtration(self):
        self.turn_off(self.args['pompe_filtration'])
        self.log("Pompe filtration OFF")
        self.run_in(self.check_stop_pompe_filtration,3)

    # Verifie que la pompe de filtration est arretee
    def check_stop_pompe_filtration(self, kwargs):
        status_filtration = self.get_state(self.args["status_filtration"])
        if status_filtration == "on":
            self.turn_off(self.args['pompe_filtration'])
            self.log("Anomalie arret pompe filtration, nouvel essai")
            self.call_service("notify/telegram_maison", message="Anomalie arret pompe filtration, nouvel essai", parse_mode='html')

    # Arret pompe filtration 
    def stop_auto(self, kwargs):
        self.stop_pompe_filtration()
    
    # Arret pompe filtration cycle manuel
    def stop_manual(self, kwargs):
        self.stop_pompe_filtration()
        self.stop_pompe_h2o2(None)
        self.set_state(self.args["manual_cycle"],state='off')
        self.set_state(self.args['mode_fonctionnement'], state='automatique')
        self.set_state(self.args["enable_solar_optimize_piscine"],state='off')
        self.run_in(self.send_enable_filtration, 60*60)
    
     # Fonction de calcul du temps de filtration en minute selon Abaque Abacus
    def compute_duree_abaque(self) -> int:
        """Advanced calculation method using an abacus.
        D = a*T^3 + b*T^2 + c*T +d
        T est forçèe a 10°C minimum
        Formule découverte dans: https://github.com/scadinot/pool
        Filtration en heures"""
        temperature = self.get_temp_max_eau()
        duree_filtration_heure = (
                0.00335 * temperature ** 3
                - 0.14953 * temperature ** 2
                + 2.43489 * temperature
                - 10.72859
        )
        duree_heure = timedelta(hours=duree_filtration_heure)*self.coeff_filtration
        str_duree_heure = self.format_timedelta(duree_heure)
        self.log(f'duree filtration {str_duree_heure}')
        self.set_state(self.args["duree_programmee"],state=str_duree_heure)
        self.temps_filtration = duree_heure
        if self.use_h2o2 :
            if temperature <= 15.0 :
                self.duree_journaliere_injection_h2o2 = 240
            else:
                self.duree_journaliere_injection_h2o2 = 430

    # format valeur timedelta en string pour affichage
    def format_timedelta(self, delta: timedelta) -> str:
        """Formats a timedelta duration to [N days] %H:%M:%S format"""
        seconds = int(delta.total_seconds())

        secs_in_a_day = 86400
        secs_in_a_hour = 3600
        secs_in_a_min = 60
        days, seconds = divmod(seconds, secs_in_a_day)
        hours, seconds = divmod(seconds, secs_in_a_hour)
        minutes, seconds = divmod(seconds, secs_in_a_min)
        time_fmt = f"{hours:02d}:{minutes:02d} H"

        if days > 0:
            suffix = "s" if days > 1 else ""
            return f"{days} day{suffix} {time_fmt}"
        return time_fmt


