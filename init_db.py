import sqlite3
import bcrypt
import os


def init_database(db_path):
    db = sqlite3.connect(db_path)
    cur = db.cursor()

    cur.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL, role TEXT DEFAULT 'user', last_login TEXT
        );
        CREATE TABLE IF NOT EXISTS disaster_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disaster_type TEXT NOT NULL, description TEXT, causes TEXT, impacts TEXT,
            case_study TEXT, lessons TEXT, dos TEXT, donts TEXT, continent TEXT, state TEXT
        );
        CREATE TABLE IF NOT EXISTS disaster_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disaster_type TEXT NOT NULL, question TEXT NOT NULL,
            option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT,
            correct_answer TEXT, exercise_number INTEGER
        );
        CREATE TABLE IF NOT EXISTS disaster_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, disaster_type TEXT, exercise_number INTEGER,
            score INTEGER, total INTEGER, taken_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, message TEXT, admin_reply TEXT, ignored INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, message TEXT NOT NULL,
            severity TEXT DEFAULT 'medium', location TEXT,
            created_at TEXT DEFAULT (datetime('now')), is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS emergency_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, number TEXT NOT NULL,
            category TEXT, description TEXT, region TEXT
        );
        CREATE TABLE IF NOT EXISTS shelters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, address TEXT, city TEXT, state TEXT,
            capacity INTEGER, current_occupancy INTEGER DEFAULT 0,
            contact TEXT, disaster_type TEXT, is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS incident_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, incident_type TEXT NOT NULL,
            location TEXT NOT NULL, description TEXT NOT NULL,
            severity TEXT DEFAULT 'medium', contact_number TEXT,
            reported_at TEXT DEFAULT (datetime('now')), status TEXT DEFAULT 'pending'
        );
        CREATE TABLE IF NOT EXISTS disaster_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            disaster_type TEXT NOT NULL UNIQUE,
            warning_signs TEXT, safety_kit TEXT, myths_facts TEXT, region_tips TEXT
        );
        CREATE TABLE IF NOT EXISTS preparedness_checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL, item TEXT NOT NULL,
            description TEXT, priority TEXT DEFAULT 'essential'
        );
    ''')

    # Seed admin accounts
    for row in [
        ('Admin', 'admin@disaster.edu', 'admin123', 'admin'),
        ('Admin', 'admin@gmail.com', 'admin123', 'admin'),
        ('Demo User', 'user@disaster.edu', 'user123', 'user'),
    ]:
        cur.execute("SELECT id FROM users WHERE email=?", (row[1],))
        if not cur.fetchone():
            pw = bcrypt.hashpw(row[2].encode(), bcrypt.gensalt()).decode()
            cur.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                        (row[0], row[1], pw, row[3]))

    cur.execute("SELECT COUNT(*) FROM disaster_details")
    if cur.fetchone()[0] == 0:
        disasters = [
            ('Earthquake','Shaking of the Earth surface from sudden energy release in the lithosphere.',
             'Tectonic plate movements, volcanic activity, fault lines, induced seismicity',
             'Building collapse, landslides, tsunamis, fires, infrastructure damage',
             '2001 Gujarat earthquake (Mw 7.7) killed over 20,000 people and left 600,000 homeless.',
             'Build earthquake-resistant structures, conduct drills, early warning systems',
             'Drop, Cover, Hold On. Move away from glass. Stay indoors until shaking stops.',
             'Do not run outside during shaking. Do not use elevators after quake.','Asia','Gujarat'),
            ('Flood','Overflow of water submerging usually dry land.',
             'Heavy rainfall, river overflow, dam failure, storm surges, poor drainage',
             'Displacement, waterborne diseases, crop damage, infrastructure loss',
             '2018 Kerala floods affected 5.4 million people, 483 deaths, Rs 40,000 crore damage.',
             'Flood warning systems, proper drainage, avoid flood-plain construction',
             'Move to higher ground. Avoid flood waters. Listen to emergency broadcasts. Boil water.',
             'Do not swim across flowing water. Do not touch electrical equipment in wet areas.',
             'Asia','Kerala'),
            ('Cyclone','Large-scale rotating air mass with low pressure center bringing devastating winds.',
             'Warm ocean waters, atmospheric instability, low pressure, Coriolis effect',
             'Storm surge, flooding, infrastructure destruction, crop loss, coastal erosion',
             'Cyclone Fani (2019) hit Odisha with 250 km/h winds, affecting 28 million.',
             'Strong coastal infrastructure, mangrove forests, evacuation plans',
             'Stay indoors. Board windows. Stock emergency supplies. Evacuate if ordered.',
             'Do not go outside during eye of storm. Do not ignore evacuation orders.','Asia','Odisha'),
            ('Tsunami','Series of ocean waves from large-scale ocean disturbances.',
             'Underwater earthquakes, volcanic eruptions, submarine landslides',
             'Massive coastal flooding, infrastructure destruction, loss of life',
             '2004 Indian Ocean tsunami killed 230,000+ across 14 countries.',
             'Tsunami warning systems, sea walls, community evacuation routes',
             'Move to high ground immediately. Listen for official warnings. Stay away from shore.',
             'Do not stay near beach. Do not return to low ground too soon.','Asia','Tamil Nadu'),
            ('Landslide','Rapid movement of rock, debris or earth down a slope.',
             'Heavy rainfall, deforestation, mining, earthquakes, soil erosion',
             'Property destruction, blocked roads, casualties, agricultural damage',
             '2014 Malin village landslide in Pune killed 151 people after torrential rain.',
             'Prevent deforestation on slopes, improve drainage, early warning systems',
             'Move away from landslide path. Move to stable high ground. Listen for rumbling.',
             'Do not build on steep slopes. Do not remove hillside vegetation.','Asia','Maharashtra'),
            ('Drought','Prolonged period of abnormally low rainfall leading to water shortage.',
             'Below-average precipitation, climate change, deforestation, over-extraction',
             'Crop failure, famine, water scarcity, livestock death, migration',
             'Maharashtra drought 2016 affected over 15,000 villages and caused farmer distress.',
             'Water conservation, drought-resistant crops, rainwater harvesting',
             'Conserve water. Use drip irrigation. Store water during monsoon.',
             'Do not waste water. Do not over-exploit groundwater.','Asia','Rajasthan'),
            ('Fire','Uncontrolled fire threatening life, property and environment.',
             'Electrical faults, gas leaks, arson, industrial accidents, negligence',
             'Loss of life, property damage, air pollution, toxic fumes',
             'Uphaar Cinema fire (1997) Delhi killed 59 due to electrical fault.',
             'Fire alarms, extinguishers, drills, clear emergency exits',
             'Evacuate immediately. Call 101. Cover nose with wet cloth. Stay low.',
             'Do not use elevators. Do not open hot doors. Do not re-enter until cleared.','Asia','Delhi'),
            ('Wildfire','Uncontrolled fire in wildland areas spreading rapidly through vegetation.',
             'Dry conditions, lightning, human carelessness, strong winds, climate change',
             'Habitat destruction, air quality degradation, property loss, respiratory illness',
             '2020 Australian bushfires burned 46 million acres and killed 3 billion animals.',
             'Create firebreaks, manage vegetation, fire-resistant buildings, evacuation plans',
             'Evacuate early. Close all windows and doors. Wear protective clothing.',
             'Do not attempt to fight large fires alone. Do not leave embers unattended.',
             'Australia','Uttarakhand'),
            ('Tornado','Rapidly rotating column of air extending from thunderstorm to ground.',
             'Severe thunderstorms, wind shear, atmospheric instability',
             'Building destruction, flying debris, power outages, casualties',
             '1989 Daulatpur-Saturia tornado in Bangladesh killed 1,300 people.',
             'Build storm shelters, develop warning systems, community preparedness',
             'Go to basement or interior room. Stay away from windows. Cover your head.',
             'Do not try to outrun a tornado. Do not open windows to equalize pressure.',
             'North America','West Bengal'),
            ('Heatwave','Prolonged period of excessively hot weather causing illness and death.',
             'Climate change, urban heat island effect, high pressure systems',
             'Heat stroke, dehydration, mortality, crop failure, economic loss',
             '2015 Indian heat wave killed 2,500+ in Andhra Pradesh and Telangana.',
             'Heat action plans, public cooling centers, awareness campaigns',
             'Stay hydrated. Avoid outdoor activity 11am-4pm. Wear light clothing.',
             'Do not leave children in parked cars. Do not ignore heat stroke symptoms.',
             'Asia','Andhra Pradesh'),
        ]
        cur.executemany(
            "INSERT INTO disaster_details (disaster_type,description,causes,impacts,case_study,lessons,dos,donts,continent,state) VALUES (?,?,?,?,?,?,?,?,?,?)",
            disasters)

    cur.execute("SELECT COUNT(*) FROM disaster_questions")
    if cur.fetchone()[0] == 0:
        questions = [
            ('Earthquake','What should you do during an earthquake?','Run outside','Drop, Cover, Hold On','Call someone','Stand near window','B',1),
            ('Earthquake','What causes most earthquakes?','Wind','Tectonic plate movements','Ocean currents','Rainfall','B',1),
            ('Earthquake','Which scale measures earthquake magnitude?','Beaufort','Richter','Fahrenheit','Decibel','B',1),
            ('Earthquake','What is the point on surface directly above earthquake origin?','Focus','Fault','Epicenter','Rift','C',1),
            ('Earthquake','Which building material is safest in earthquake zones?','Brick','Reinforced concrete','Wood only','Glass','B',1),
            ('Earthquake','What is seismology?','Study of volcanoes','Study of earthquakes','Study of weather','Study of oceans','B',2),
            ('Earthquake','After an earthquake, you should check for?','Gas leaks','New paint','Wi-Fi signal','TV channels','A',2),
            ('Earthquake','What is liquefaction?','Ice melting','Soil behaving like liquid','Water boiling','Rock formation','B',2),
            ('Earthquake','Which is NOT caused by earthquakes?','Tsunamis','Landslides','Hurricanes','Ground rupture','C',2),
            ('Earthquake','Emergency kit should include?','Gaming console','Water and first aid','Books','Furniture','B',2),
            ('Flood','What is a flash flood?','Slow rising water','Sudden rapid flooding','Ocean tide','Dam storage','B',1),
            ('Flood','What should you avoid during floods?','High ground','Walking through flood water','Emergency radio','Evacuation','B',1),
            ('Flood','Which disease spreads most after floods?','Diabetes','Cholera','Asthma','Arthritis','B',1),
            ('Flood','What depth of moving water can knock you down?','1 foot','6 inches','5 feet','10 feet','B',1),
            ('Flood','Best action when flood warning is issued?','Go swimming','Move to higher ground','Stay in basement','Open windows','B',1),
            ('Flood','What is a flood plain?','Mountain top','Area prone to flooding','Desert','Forest','B',2),
            ('Flood','How many inches of water can float a car?','1 inch','6 inches','12 inches','36 inches','C',2),
            ('Flood','After floods, tap water may be?','Perfectly safe','Contaminated','Carbonated','Frozen','B',2),
            ('Flood','What helps prevent urban floods?','Concrete everywhere','Proper drainage systems','Removing trees','Blocking rivers','B',2),
            ('Flood','What is a levee?','Type of boat','Embankment to prevent flooding','Weather instrument','Rescue tool','B',2),
            ('Cyclone','What is the center of a cyclone called?','Core','Eye','Heart','Focus','B',1),
            ('Cyclone','Cyclones form over?','Mountains','Warm ocean waters','Deserts','Frozen lakes','B',1),
            ('Cyclone','Which instrument measures wind speed?','Barometer','Anemometer','Thermometer','Seismometer','B',1),
            ('Cyclone','What should you do during a cyclone?','Go to the beach','Stay indoors away from windows','Drive around','Fly a kite','B',1),
            ('Cyclone','Storm surge is?','Normal waves','Abnormal rise in sea level','Underground water','Rain water','B',1),
            ('Tsunami','First warning sign of a tsunami?','Heavy rain','Sudden withdrawal of sea water','Strong wind','Dark clouds','B',1),
            ('Tsunami','What causes most tsunamis?','Wind storms','Underwater earthquakes','Tidal changes','Meteor showers','B',1),
            ('Tsunami','If you feel a strong earthquake near coast?','Stay and watch sea','Move immediately to high ground','Call friends first','Wait for warning','B',1),
            ('Tsunami','Tsunami waves can travel at?','10 km/h','100 km/h','800 km/h','5 km/h','C',1),
            ('Tsunami','The first tsunami wave is?','Always the largest','Often not the largest','Always the smallest','Harmless','B',1),
            ('Heatwave','What is heat stroke?','Small burn','Life-threatening from overheating','Normal temperature','Mild dehydration','B',1),
            ('Heatwave','Best fluid to drink during heatwave?','Alcohol','Water with electrolytes','Coffee','Soda','B',1),
            ('Heatwave','Best clothing color during heatwave?','Black','Dark blue','Light or white','Red','C',1),
            ('Heatwave','Most dangerous outdoor hours during heatwave?','Early morning','11 AM to 4 PM','Evening','Midnight','B',1),
            ('Heatwave','Urban areas experience more heat due to?','Less rainfall','Heat island effect','More people','Higher altitude','B',1),
        ]
        cur.executemany(
            "INSERT INTO disaster_questions (disaster_type,question,option_a,option_b,option_c,option_d,correct_answer,exercise_number) VALUES (?,?,?,?,?,?,?,?)",
            questions)

    cur.execute("SELECT COUNT(*) FROM alerts")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO alerts (title,message,severity,location) VALUES (?,?,?,?)", [
            ('Cyclone Warning - Bay of Bengal',
             'A category 3 cyclone is expected to make landfall on the Odisha coast within 48 hours. Residents in coastal areas should evacuate immediately to designated shelters.',
             'critical','Odisha, West Bengal Coast'),
            ('Flood Alert - Brahmaputra River',
             'Water levels in Brahmaputra have crossed the danger mark at Guwahati. Low-lying areas in Assam at risk. Avoid river banks.',
             'high','Assam'),
            ('Heatwave Advisory - North India',
             'Temperatures expected to exceed 45 degrees C in Rajasthan and Gujarat. Stay hydrated, avoid outdoor activity 11am-4pm.',
             'medium','Rajasthan, Gujarat'),
            ('Earthquake Aftershock Notice',
             'Minor aftershocks M3.5-4.0 expected after yesterday earthquake. No major damage expected but exercise caution.',
             'low','Gujarat'),
            ('Heavy Rainfall Warning - South Coast',
             'IMD forecasts heavy to very heavy rainfall along Kerala and Karnataka coast over next 72 hours. Fishermen advised not to venture into sea.',
             'high','Kerala, Karnataka'),
        ])

    cur.execute("SELECT COUNT(*) FROM emergency_contacts")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO emergency_contacts (name,number,category,description,region) VALUES (?,?,?,?,?)", [
            ('National Emergency Number','112','national','Single emergency number for police, fire and ambulance','All India'),
            ('NDMA Disaster Helpline','1078','disaster','National Disaster Management Authority helpline','All India'),
            ('Police Emergency','100','police','Police emergency response helpline','All India'),
            ('Ambulance / Medical Emergency','102','medical','Free ambulance service across India','All India'),
            ('Fire Department','101','fire','Fire and rescue emergency services','All India'),
            ('NDRF Flood Operations','9711077372','disaster','National Disaster Response Force flood operations','All India'),
            ('Poison Control Centre','1800-116-117','medical','24-hour poison information and treatment guidance','All India'),
            ('Women Distress Helpline','1091','safety','Women emergency and distress helpline','All India'),
            ('Childline Emergency','1098','safety','Child distress and emergency assistance helpline','All India'),
            ('Road Accident Emergency','1073','national','National highway accident emergency response','All India'),
            ('Gujarat Disaster Helpline','1070','disaster','Gujarat State Disaster Management Authority','Gujarat'),
            ('Kerala State DM Authority','1077','disaster','Kerala State Disaster Management Authority','Kerala'),
            ('Maharashtra Emergency Cell','022-22694726','disaster','Maharashtra state emergency disaster control cell','Maharashtra'),
            ('Coast Guard Emergency','1554','disaster','Indian Coast Guard maritime and coastal emergencies','Coastal India'),
        ])

    cur.execute("SELECT COUNT(*) FROM shelters")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO shelters (name,address,city,state,capacity,current_occupancy,contact,disaster_type,is_active) VALUES (?,?,?,?,?,?,?,?,?)", [
            ('Rajiv Gandhi Stadium Shelter','MG Road, Stadium Complex','Bhubaneswar','Odisha',5000,1200,'0674-2301234','Cyclone',1),
            ('Community Hall Emergency Shelter','Sector 15, NH-44','Guwahati','Assam',800,340,'0361-2345678','Flood',1),
            ('Govt School Shelter Camp','Village Anandpur, Tehsil Anjad','Barwani','Madhya Pradesh',300,0,'07283-234567','Flood',1),
            ('Cyclone Permanent Shelter C-14','Beach Road, East Coast','Puri','Odisha',2000,450,'06752-224680','Cyclone',1),
            ('NDRF Forward Base Camp','Near Collectorate Office','Morbi','Gujarat',1500,890,'02822-221234','Earthquake',1),
            ('Relief Camp Perumbavoor','Perumbavoor Taluk Office Grounds','Ernakulam','Kerala',600,220,'0484-2455634','Flood',1),
            ('Municipal Shelter Ground','Near Bus Stand','Shirdi','Maharashtra',1200,0,'02423-258634','Flood',0),
            ('Hill District Emergency Camp','District HQ Compound','Shimla','Himachal Pradesh',400,180,'0177-2651234','Landslide',1),
        ])

    cur.execute("SELECT COUNT(*) FROM preparedness_checklists")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO preparedness_checklists (category,item,description,priority) VALUES (?,?,?,?)", [
            ('Water and Food','Store 3-day water supply (4L/person/day)','Minimum 72 hours of clean drinking water per person','essential'),
            ('Water and Food','Non-perishable food for 3 days','Canned goods, dry goods, energy bars requiring no cooking','essential'),
            ('Water and Food','Manual can opener','Electric openers will not work in power outages','essential'),
            ('Water and Food','Water purification tablets','Treat contaminated water during and after floods','important'),
            ('Water and Food','Baby food or formula if applicable','Age-appropriate emergency food for infants','essential'),
            ('First Aid','First aid kit with bandages, antiseptic, gauze','Prepackaged kits available at pharmacies','essential'),
            ('First Aid','Prescription medications 7-day supply','Critical for chronic illness management during disasters','essential'),
            ('First Aid','Pain relievers and fever reducers','Over-the-counter medications for common ailments','important'),
            ('First Aid','Thermometer and blood pressure monitor','Monitor health without doctor access','important'),
            ('First Aid','Oral rehydration salts ORS','Treat dehydration during heatwave or after diarrhoea','important'),
            ('Documents','Copies of ID documents Aadhar PAN Passport','Keep waterproof photocopies in emergency kit','essential'),
            ('Documents','Insurance policies and property documents','Needed for claims after disaster','essential'),
            ('Documents','Emergency contact list written not just digital','Physical list in case phone dies or is lost','essential'),
            ('Documents','Bank account and card details','For financial access during evacuation','important'),
            ('Communication','Battery-powered or hand-crank AM/FM radio','Receive emergency broadcasts without electricity','essential'),
            ('Communication','Extra phone chargers and power bank 10000mAh','Maintain communication capability','essential'),
            ('Communication','Whistle to signal for help','Sound travels far useful if trapped under debris','important'),
            ('Communication','Written list of local emergency numbers','Backup when smartphone is unavailable','essential'),
            ('Safety Equipment','Flashlights and extra batteries','One per family member plus spares','essential'),
            ('Safety Equipment','Dust masks N95 respirators','For smoke ash or poor air quality emergencies','important'),
            ('Safety Equipment','Plastic sheeting and duct tape','For shelter-in-place or sealing broken windows','important'),
            ('Safety Equipment','Work gloves for debris clearing','Protect hands during cleanup operations','important'),
            ('Sanitation','Moist towelettes and hand sanitizer','Maintain hygiene when water is unavailable','essential'),
            ('Sanitation','Garbage bags and plastic ties','Manage waste during extended displacement','important'),
            ('Sanitation','Toilet paper and feminine hygiene products','Essential sanitation supplies for all ages','essential'),
            ('Sanitation','Soap toothbrush toothpaste','Basic hygiene to prevent disease spread','essential'),
        ])

    cur.execute("SELECT COUNT(*) FROM disaster_articles")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO disaster_articles (disaster_type,warning_signs,safety_kit,myths_facts,region_tips) VALUES (?,?,?,?,?)", [
            ('Earthquake',
             'Ground shaking or rumbling sound|Objects falling from shelves|Swaying of buildings or trees|Animals behaving strangely|Cracks appearing in walls or ground',
             'Water 4L/person/day|First aid kit|Flashlight with batteries|Whistle|Dust mask N95|Wrench to turn off gas|Moist towelettes|Phone charger and power bank|Cash in small denominations|Fire extinguisher',
             'MYTH: Stand in a doorway. FACT: Modern buildings are safe throughout - get under a sturdy table.|MYTH: A big quake means no more small ones. FACT: Large earthquakes have dangerous aftershocks.|MYTH: Certain areas are completely safe. FACT: Any region can experience tremors.',
             'GUJARAT Zone IV/V: Build to IS-1893 standards. Conduct annual community drills.|HIMALAYAN STATES Zone V: Highest risk. Register with district emergency management.|NORTH-EAST: High seismic zone. Know your panchayat disaster management plan.'),
            ('Flood',
             'Heavy rainfall lasting several days|Rapidly rising river or stream levels|Overflowing drainage systems|Water entering low-lying areas|Muddy river water|Animals moving to higher ground',
             'Water purification tablets|Waterproof bag for documents|Life jackets|Strong rope 10 metres|First aid kit and medications|Battery-powered radio|Food rations 7 days|Rubber boots and raincoat',
             'MYTH: Flood water is just dirty water. FACT: Contains sewage and pathogens - deadly without protection.|MYTH: You can drive through shallow flood water. FACT: 30cm can knock you down 60cm sweeps a car away.|MYTH: Floods only affect river banks. FACT: Urban flooding can affect any poorly drained area.',
             'KERALA: Monsoon June-Sept critical. Know your panchayat evacuation route.|ASSAM BRAHMAPUTRA BELT: Annual flooding expected. Store supplies on upper floors before June.|MUMBAI: Urban flood risk peaks June-July. Avoid low-lying roads during heavy rain.'),
            ('Cyclone',
             'Sudden drop in temperature|Unusual swell in the sea|Strong gusty winds|Darkening sky with fast clouds|Heavy widespread rainfall|Official cyclone alerts from IMD',
             'Battery radio for updates|Flashlight and batteries|First aid kit|Non-perishable food 7 days|Large water containers pre-filled|Strong ropes and tarpaulin|Documents in waterproof bag|Life jackets for coastal residents',
             'MYTH: The calm eye means the storm is over. FACT: The eye passes and the back wall is equally dangerous.|MYTH: Upper floors are safer. FACT: Move to ground floor interior room away from windows.|MYTH: Cyclone forecasts are inaccurate. FACT: IMD cyclone forecasts are now 85 percent accurate 48 hours ahead.',
             'ODISHA COAST: Highest cyclone risk in India. Follow OSDMA advisories. Know nearest cyclone shelter.|TAMIL NADU: Bay of Bengal cyclone season Oct-Dec. Board windows early.|GUJARAT SAURASHTRA: Arabian Sea cyclones rarer but severe. Pre-position supplies before June.'),
            ('Heatwave',
             'Temperature 4.5 degrees C above normal for 2 or more days|High humidity with no cooling at night|Heat action plan activated|Increased reports of heat illness|Hot dry Loo winds in North India',
             'Oral rehydration salts ORS|Water bottles drink before feeling thirsty|Electrolyte drinks or coconut water|Light loose light-coloured cotton clothing|Wide brim hat and UV sunglasses|Sunscreen SPF 30+|Cooling towel or wet cloth',
             'MYTH: Heat stroke only happens in the sun. FACT: Can occur indoors without air conditioning.|MYTH: Alcohol helps you cool down. FACT: Alcohol causes dehydration and raises core temperature.|MYTH: If you feel fine you are not at risk. FACT: Heat stroke can come on suddenly without warning.',
             'RAJASTHAN GUJARAT: Extreme heat risk. Loo winds are dangerous. Check on elderly neighbours daily.|ANDHRA TELANGANA: Highest heat mortality in India. Cooling centres mandatory in cities.|DELHI NCR: Urban heat island significantly raises risk. Avoid metal surfaces and parked vehicles.'),
            ('Tsunami',
             'Strong earthquake felt near coast|Sudden unusual withdrawal of sea water|Loud roaring sound from ocean|Rapid rise in water level|Abnormal wave behaviour',
             'Emergency Go-Bag with 72-hour supplies|Strong shoes|Life jacket|Waterproof bag for documents|Battery radio|First aid kit|Rope|High-energy food bars|Whistle',
             'MYTH: A tsunami is a single giant wave. FACT: It is a series of waves sometimes 20 minutes apart - the first is rarely the largest.|MYTH: Surfers and strong swimmers are safe. FACT: Even expert swimmers cannot survive tsunami currents.|MYTH: Tsunamis always look like walls of water. FACT: Often appear as rapidly rising water.',
             'ANDAMAN AND NICOBAR: Highest risk in India. Practice vertical evacuation to upper concrete floors.|TAMIL NADU ANDHRA COAST: Know nearest high ground at least 30 metres elevation.|KERALA KARNATAKA: Follow all alerts. Bay of Bengal earthquake can generate tsunamis in 2 hours.'),
        ])

    db.commit()
    db.close()
