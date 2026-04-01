import sqlite3
import bcrypt
import os

def init_database(db_path):
    """Initialize SQLite database with schema and sample data."""
    if os.path.exists(db_path):
        return

    db = sqlite3.connect(db_path)
    cur = db.cursor()

    # ---- SCHEMA ----
    cur.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            last_login TEXT
        );
        CREATE TABLE IF NOT EXISTS disaster_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disaster_type TEXT NOT NULL,
            description TEXT, causes TEXT, impacts TEXT,
            case_study TEXT, lessons TEXT, dos TEXT, donts TEXT,
            continent TEXT, state TEXT
        );
        CREATE TABLE IF NOT EXISTS disaster_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disaster_type TEXT NOT NULL,
            question TEXT NOT NULL,
            option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
            correct_answer TEXT,
            exercise_number INTEGER
        );
        CREATE TABLE IF NOT EXISTS disaster_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, disaster_type TEXT,
            exercise_number INTEGER, score INTEGER, total INTEGER,
            taken_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, message TEXT, admin_reply TEXT
        );
    ''')

    # ---- SEED ADMIN & DEMO USER ----
    admin_pw = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt()).decode()
    user_pw = bcrypt.hashpw('user123'.encode(), bcrypt.gensalt()).decode()
    cur.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,'admin')",
                ('Admin','admin@disaster.edu', admin_pw))
    cur.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,'user')",
                ('Demo User','user@disaster.edu', user_pw))

    # ---- SEED DISASTER DETAILS ----
    disasters = [
        ('Earthquake',
         'Shaking of Earth surface from sudden energy release in the lithosphere.',
         'Tectonic plate movements, volcanic activity, fault lines',
         'Building collapse, landslides, tsunamis, loss of life',
         '2001 Gujarat earthquake (Mw 7.7) killed over 20,000 people.',
         'Build earthquake-resistant structures, conduct drills, early warning systems',
         'Drop, Cover, Hold On. Move away from glass. Stay indoors.',
         'Do not run outside during shaking. Do not use elevators.',
         'Asia','Gujarat'),
        ('Flood',
         'Overflow of water submerging usually dry land.',
         'Heavy rainfall, river overflow, dam failure, storm surges',
         'Displacement, waterborne diseases, crop damage, economic loss',
         '2018 Kerala floods affected 5.4 million people, 483 deaths.',
         'Flood warning systems, proper drainage, avoid flood-plain construction',
         'Move to higher ground. Avoid flood waters. Listen to emergency broadcasts.',
         'Do not swim across flowing water. Do not touch electrical equipment in wet areas.',
         'Asia','Kerala'),
        ('Cyclone',
         'Large-scale rotating air mass with low pressure center bringing devastating winds.',
         'Warm ocean waters, atmospheric instability, low pressure, Coriolis effect',
         'Storm surge, flooding, infrastructure destruction, coastal erosion',
         'Cyclone Fani (2019) hit Odisha with 250 km/h winds, affecting 28 million.',
         'Strong coastal infrastructure, mangrove forests, evacuation plans',
         'Stay indoors. Board windows. Stock emergency supplies.',
         'Do not go outside during eye of storm. Do not ignore evacuation orders.',
         'Asia','Odisha'),
        ('Tsunami',
         'Series of ocean waves from large-scale ocean disturbances.',
         'Underwater earthquakes, volcanic eruptions, submarine landslides',
         'Massive coastal flooding, infrastructure destruction, loss of life',
         '2004 Indian Ocean tsunami killed 230,000+ across 14 countries.',
         'Tsunami warning systems, sea walls, educate communities on evacuation',
         'Move to high ground immediately. Listen for official warnings.',
         'Do not stay near beach. Do not return to low ground too soon.',
         'Asia','Tamil Nadu'),
        ('Landslide',
         'Movement of rock, debris or earth down a slope due to gravity.',
         'Heavy rainfall, deforestation, mining, earthquakes',
         'Property destruction, blocked roads, casualties',
         '2014 Malin village landslide in Pune killed 151 people.',
         'Avoid deforestation on slopes, improve drainage, early warning systems',
         'Move away from landslide path. Move to stable ground.',
         'Do not build on steep slopes. Do not remove hillside vegetation.',
         'Asia','Maharashtra'),
        ('Drought',
         'Prolonged period of abnormally low rainfall leading to water shortage.',
         'Below-average precipitation, high temperatures, climate change',
         'Crop failure, famine, water scarcity, migration',
         'Maharashtra drought 2016 affected over 15,000 villages.',
         'Water conservation, drought-resistant crops, rainwater harvesting',
         'Conserve water. Use drip irrigation. Store water during monsoon.',
         'Do not waste water. Do not over-exploit groundwater.',
         'Asia','Rajasthan'),
        ('Fire',
         'Uncontrolled fire threatening life, property and environment.',
         'Electrical faults, gas leaks, arson, industrial accidents',
         'Loss of life, property damage, air pollution',
         'Uphaar Cinema fire (1997) Delhi killed 59 people.',
         'Fire alarms, extinguishers, fire drills, proper exits',
         'Evacuate immediately. Call fire department. Cover nose with wet cloth.',
         'Do not use elevators. Do not open hot doors.',
         'Asia','Delhi'),
        ('Wildfire',
         'Uncontrolled fire in wildland areas spreading rapidly through vegetation.',
         'Dry conditions, lightning, human carelessness, strong winds',
         'Habitat destruction, air quality degradation, property loss',
         '2020 Australian bushfires burned 46 million acres.',
         'Create firebreaks, manage vegetation, have evacuation plans',
         'Evacuate early. Close all windows and doors. Wear protective clothing.',
         'Do not attempt to fight large fires alone. Do not leave embers unattended.',
         'Australia','Uttarakhand'),
        ('Tornado',
         'Rapidly rotating column of air extending from thunderstorm to ground.',
         'Severe thunderstorms, wind shear, atmospheric instability',
         'Building destruction, flying debris, power outages',
         '1989 Daulatpur-Saturia tornado in Bangladesh killed 1,300.',
         'Build storm shelters, develop warning systems, community preparedness',
         'Go to basement or interior room. Stay away from windows.',
         'Do not try to outrun a tornado on foot. Do not open windows.',
         'North America','West Bengal'),
        ('Heatwave',
         'Prolonged period of excessively hot weather causing illness and death.',
         'Climate change, urban heat island effect, high pressure systems',
         'Heat stroke, dehydration, mortality, crop failure',
         '2015 Indian heat wave killed 2,500+ in Andhra Pradesh and Telangana.',
         'Heat action plans, public cooling centers, awareness campaigns',
         'Stay hydrated. Avoid outdoor activity during peak hours.',
         'Do not leave children in parked cars. Do not ignore heat stroke symptoms.',
         'Asia','Andhra Pradesh'),
    ]
    cur.executemany(
        "INSERT INTO disaster_details (disaster_type,description,causes,impacts,case_study,lessons,dos,donts,continent,state) VALUES (?,?,?,?,?,?,?,?,?,?)",
        disasters
    )

    # ---- SEED QUESTIONS (2 exercises x 5 questions each for Earthquake & Flood) ----
    questions = [
        # Earthquake Exercise 1
        ('Earthquake','What should you do during an earthquake?','Run outside','Drop, Cover, Hold On','Call someone','Stand near window','B',1),
        ('Earthquake','What causes most earthquakes?','Wind','Tectonic plate movements','Ocean currents','Rainfall','B',1),
        ('Earthquake','Which scale measures earthquake magnitude?','Beaufort','Richter','Fahrenheit','Decibel','B',1),
        ('Earthquake','What is the point on surface directly above earthquake origin?','Focus','Fault','Epicenter','Rift','C',1),
        ('Earthquake','Which building material is safest in earthquake zones?','Brick','Reinforced concrete','Wood only','Glass','B',1),
        # Earthquake Exercise 2
        ('Earthquake','What is seismology?','Study of volcanoes','Study of earthquakes','Study of weather','Study of oceans','B',2),
        ('Earthquake','After an earthquake, you should check for?','Gas leaks','New paint','Wi-Fi signal','TV channels','A',2),
        ('Earthquake','What is liquefaction?','Ice melting','Soil behaving like liquid','Water boiling','Rock formation','B',2),
        ('Earthquake','Which is NOT caused by earthquakes?','Tsunamis','Landslides','Hurricanes','Ground rupture','C',2),
        ('Earthquake','Emergency kit should include?','Gaming console','Water and first aid','Books','Furniture','B',2),
        # Flood Exercise 1
        ('Flood','What is a flash flood?','Slow rising water','Sudden rapid flooding','Ocean tide','Dam storage','B',1),
        ('Flood','What should you avoid during floods?','High ground','Walking through flood water','Emergency radio','Evacuation','B',1),
        ('Flood','Which disease spreads most after floods?','Diabetes','Cholera','Asthma','Arthritis','B',1),
        ('Flood','What depth of moving water can knock you down?','1 foot','6 inches','5 feet','10 feet','B',1),
        ('Flood','Best action when flood warning is issued?','Go swimming','Move to higher ground','Stay in basement','Open windows','B',1),
        # Flood Exercise 2
        ('Flood','What is a flood plain?','Mountain top','Area prone to flooding','Desert','Forest','B',2),
        ('Flood','How many inches of water can float a car?','1 inch','6 inches','12 inches','36 inches','C',2),
        ('Flood','After floods, tap water may be?','Perfectly safe','Contaminated','Carbonated','Frozen','B',2),
        ('Flood','What helps prevent urban floods?','Concrete everywhere','Proper drainage systems','Removing trees','Blocking rivers','B',2),
        ('Flood','What is a levee?','Type of boat','Embankment to prevent flooding','Weather instrument','Rescue tool','B',2),
        # Cyclone Exercise 1
        ('Cyclone','What is the center of a cyclone called?','Core','Eye','Heart','Focus','B',1),
        ('Cyclone','Cyclones form over?','Mountains','Warm ocean waters','Deserts','Frozen lakes','B',1),
        ('Cyclone','Which instrument measures wind speed?','Barometer','Anemometer','Thermometer','Seismometer','B',1),
        ('Cyclone','What should you do during a cyclone?','Go to the beach','Stay indoors away from windows','Drive around','Fly a kite','B',1),
        ('Cyclone','Storm surge is?','Normal waves','Abnormal rise in sea level','Underground water','Rain water','B',1),
    ]
    cur.executemany(
        "INSERT INTO disaster_questions (disaster_type,question,option_a,option_b,option_c,option_d,correct_answer,exercise_number) VALUES (?,?,?,?,?,?,?,?)",
        questions
    )

    db.commit()
    db.close()
