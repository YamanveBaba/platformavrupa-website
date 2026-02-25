/* --------------------------------------------------------------------------
   PLATFORM AVRUPA - GENEL VERİTABANI (FINAL - ULTRA SÜRÜM)
   1. Kısım: 30 Avrupa Ülkesi ve Şehirleri (KORUNDU)
   2. Kısım: 120+ Marka ve 3500+ Model Araç Listesi (GÜNCELLENDİ)
-------------------------------------------------------------------------- */

const lokasyonVeritabani = {
    "DE": { 
        isim: "Almanya", bayrak: "🇩🇪", tel: "+49", para: "EUR",
        sehirler: ["Augsburg", "Berlin", "Bochum", "Bonn", "Brandenburg an der Havel", "Braunschweig", "Bremen", "Bremerhaven", "Chemnitz", "Cottbus", "Darmstadt", "Dortmund", "Dresden", "Duisburg", "Düsseldorf", "Erfurt", "Essen", "Flensburg", "Frankfurt (Oder)", "Frankfurt am Main", "Freiburg", "Gera", "Göttingen", "Halle (Saale)", "Hamburg", "Hannover", "Heidelberg", "Ingolstadt", "Jena", "Karlsruhe", "Kassel", "Kiel", "Koblenz", "Köln", "Leipzig", "Ludwigshafen", "Lübeck", "Magdeburg", "Mainz", "Mannheim", "München", "Münster", "Neubrandenburg", "Neunkirchen", "Nürnberg", "Offenbach", "Oldenburg", "Osnabrück", "Potsdam", "Regensburg", "Rostock", "Saarbrücken", "Schwerin", "Stuttgart", "Trier", "Ulm", "Wiesbaden", "Würzburg"]
    },
    "AT": { 
        isim: "Avusturya", bayrak: "🇦🇹", tel: "+43", para: "EUR",
        sehirler: ["Amstetten", "Bregenz", "Dornbirn", "Eisenstadt", "Feldkirch", "Graz", "Hallein", "Innsbruck", "Kapfenberg", "Klagenfurt", "Krems an der Donau", "Leoben", "Linz", "Lustenau", "Mödling", "Salzburg", "Sankt Pölten", "Schwechat", "Steyr", "Traun", "Tulln an der Donau", "Villach", "Wels", "Wien (Viyana)", "Wolfsberg"]
    },
    "BE": { 
        isim: "Belçika", bayrak: "🇧🇪", tel: "+32", para: "EUR",
        sehirler: ["Aalst", "Anderlecht", "Antwerpen", "Arlon", "Binche", "Brugge", "Brussels (Bruxelles)", "Charleroi", "Dilbeek", "Etterbeek", "Eupen", "Genk", "Gent", "Hasselt", "Heist-op-den-Berg", "Ixelles", "Knokke-Heist", "Kortrijk", "La Louvière", "Leuven", "Liège", "Mechelen", "Molenbeek-Saint-Jean", "Mons", "Mouscron", "Namur", "Ostend (Oostende)", "Roeselare", "Schaarbeek (Schaerbeek)", "Seraing", "Sint-Niklaas", "Tournai", "Turnhout", "Uccle (Ukkel)", "Verviers", "Vilvoorde", "Wavre", "Woluwe-Saint-Lambert", "Woluwe-Saint-Pierre"]
    },
    "BG": { 
        isim: "Bulgaristan", bayrak: "🇧🇬", tel: "+359", para: "BGN",
        sehirler: ["Asenovgrad", "Blagoevgrad", "Burgas", "Dobrich", "Dupnitsa", "Gabrovo", "Haskovo", "Kardzhali", "Kyustendil", "Lovech", "Montana", "Pazardzhik", "Pernik", "Pleven", "Plovdiv", "Razgrad", "Ruse", "Shumen", "Silistra", "Simitli", "Sliven", "Smolyan", "Sofya (Sofia)", "Stara Zagora", "Targovishte", "Varna", "Veliko Tarnovo", "Vidin", "Vratsa", "Yambol"]
    },
    "CZ": { 
        isim: "Çekya", bayrak: "🇨🇿", tel: "+420", para: "CZK",
        sehirler: ["Brno", "Chomutov", "Děčín", "Frýdek-Místek", "Havířov", "Hradec Králové", "Jihlava", "Karviná", "Kladno", "Kolín", "Liberec", "Mladá Boleslav", "Most", "Olomouc", "Opava", "Ostrava", "Pardubice", "Plzeň (Pilsen)", "Prague (Praha)", "Prostějov", "Sokolov", "Teplice", "Trutnov", "Tábor", "Zlín", "České Budějovice", "Český Krumlov", "Ústí nad Labem"]
    },
    "DK": { 
        isim: "Danimarka", bayrak: "🇩🇰", tel: "+45", para: "DKK",
        sehirler: ["Aalborg", "Aarhus", "Copenhagen (Kopenhag)", "Esbjerg", "Fredericia", "Frederikshavn", "Haderslev", "Herning", "Hillerød", "Hjørring", "Holstebro", "Horsens", "Kolding", "Køge", "Nykøbing Falster", "Næstved", "Odense", "Randers", "Ringsted", "Roskilde", "Rønne", "Silkeborg", "Skive", "Slagelse", "Svendborg", "Sønderborg", "Taastrup", "Thisted", "Vejle", "Viborg"]
    },
    "EE": { 
        isim: "Estonya", bayrak: "🇪🇪", tel: "+372", para: "EUR",
        sehirler: ["Elva", "Haapsalu", "Jõhvi", "Keila", "Kohtla-Järve", "Kuressaare", "Kärdla", "Maardu", "Narva", "Paide", "Pärnu", "Rakvere", "Rapla", "Sillamäe", "Tallinn (Başkent)", "Tapa", "Tartu", "Valga", "Viljandi", "Võru"]
    },
    "FI": { 
        isim: "Finlandiya", bayrak: "🇫🇮", tel: "+358", para: "EUR",
        sehirler: ["Espoo", "Helsinki (Başkent)", "Hyvinkää", "Hämeenlinna", "Joensuu", "Jyväskylä", "Kajaani", "Kokkola", "Kotka", "Kouvola", "Kuopio", "Lahti", "Lappeenranta", "Mikkeli", "Oulu", "Pori", "Rauma", "Rovaniemi", "Saarijärvi", "Salo", "Savonlinna", "Seinäjoki", "Tampere", "Turku", "Vaasa", "Vantaa"]
    },
    "FR": { 
        isim: "Fransa", bayrak: "🇫🇷", tel: "+33", para: "EUR",
        sehirler: ["Aix-en-Provence", "Amiens", "Angers", "Argenteuil", "Avignon", "Besançon", "Bordeaux", "Brest", "Caen", "Clermont-Ferrand", "Dijon", "Grenoble", "Le Havre", "Le Mans", "Lille", "Limoges", "Lyon", "Marseille", "Metz", "Montpellier", "Montreuil", "Mulhouse", "Nancy", "Nantes", "Nice", "Nîmes", "Orléans", "Paris", "Perpignan", "Poitiers", "Reims", "Rennes", "Rouen", "Saint-Denis", "Saint-Étienne", "Strasbourg", "Toulon", "Toulouse", "Tours", "Versailles", "Villeurbanne"]
    },
    "HR": { 
        isim: "Hırvatistan", bayrak: "🇭🇷", tel: "+385", para: "EUR",
        sehirler: ["Bjelovar", "Dubrovnik", "Karlovac", "Kaštela", "Knin", "Koprivnica", "Nova Gradiška", "Osijek", "Petrinja", "Požega", "Pula", "Rijeka", "Samobor", "Sisak", "Slavonski Brod", "Solin", "Split", "Trogir", "Varaždin", "Varaždin Breg", "Vinkovci", "Vukovar", "Zadar", "Zagreb (Başkent)", "Čakovec", "Đakovo", "Šibenik"]
    },
    "NL": { 
        isim: "Hollanda", bayrak: "🇳🇱", tel: "+31", para: "EUR",
        sehirler: ["Alkmaar", "Almere", "Amersfoort", "Amsterdam", "Apeldoorn", "Arnhem", "Assen", "Born", "Breda", "Deventer", "Dordrecht", "Eindhoven", "Emmen", "Groningen", "Haarlem", "Haarlemmermeer", "Hilversum", "Hoofddorp", "Leiden", "Maastricht", "Nijmegen", "Rotterdam", "Tilburg", "Utrecht", "Velsen", "Venlo", "Zaanstad", "Zoetermeer", "Zwolle", "‘s-Hertogenbosch (Den Bosch)", "Den Haag (Lahey)"]
    },
    "GB": { 
        isim: "İngiltere", bayrak: "🇬🇧", tel: "+44", para: "GBP",
        sehirler: ["Aberdeen", "Belfast", "Birmingham", "Bradford", "Brighton", "Bristol", "Cardiff", "Coventry", "Derby", "Edinburgh", "Exeter", "Glasgow", "Kingston upon Hull (Hull)", "Leeds", "Leicester", "Liverpool", "London (Londra) – Başkent", "Luton", "Manchester", "Middlesbrough", "Milton Keynes", "Newcastle upon Tyne", "Northampton", "Norwich", "Nottingham", "Plymouth", "Portsmouth", "Reading", "Sheffield", "Southampton", "Stoke-on-Trent", "Sunderland", "Swindon", "Wolverhampton"]
    },
    "IE": { 
        isim: "İrlanda", bayrak: "🇮🇪", tel: "+353", para: "EUR",
        sehirler: ["Athlone", "Bray", "Carlow", "Castlebar", "Clonmel", "Cork", "Drogheda", "Dublin (Başkent)", "Dún Laoghaire", "Ennis", "Galway", "Kilkenny", "Letterkenny", "Limerick", "Mallow", "Mullingar", "Navan", "Nenagh", "Portlaoise", "Sligo", "Swords", "Tralee", "Waterford", "Wexford"]
    },
    "ES": { 
        isim: "İspanya", bayrak: "🇪🇸", tel: "+34", para: "EUR",
        sehirler: ["Albacete", "Alcorcón", "Alicante", "Almería", "Badajoz", "Badalona", "Barcelona", "Bilbao", "Burgos", "Cartagena", "Castellón de la Plana", "Córdoba", "Elche", "Getafe", "Gijón", "Granada", "Huelva", "Jerez de la Frontera", "L’Hospitalet de Llobregat", "La Coruña (A Coruña)", "Las Palmas de Gran Canaria", "Lleida", "Logroño", "Madrid (Başkent)", "Marbella", "Murcia", "Málaga", "Móstoles", "Oviedo", "Palma de Mallorca", "Pamplona", "Reus", "Sabadell", "Salamanca", "San Sebastián (Donostia)", "Santa Cruz de Tenerife", "Santander", "Sevilla", "Tarragona", "Terrassa", "Valencia", "Valladolid", "Vigo", "Vitoria-Gasteiz", "Zaragoza"]
    },
    "SE": { 
        isim: "İsveç", bayrak: "🇸🇪", tel: "+46", para: "SEK",
        sehirler: ["Borås", "Eskilstuna", "Gävle", "Göteborg (Gothenburg)", "Halmstad", "Helsingborg", "Jönköping", "Kalmar", "Karlstad", "Kristianstad", "Kungsbacka", "Linköping", "Luleå", "Lund", "Malmö", "Nacka", "Norrköping", "Skellefteå", "Stockholm (Başkent)", "Sundbyberg", "Sundsvall", "Södertälje", "Trollhättan", "Täby", "Umeå", "Uppsala", "Västerås", "Växjö", "Örebro", "Östersund"]
    },
    "CH": { 
        isim: "İsviçre", bayrak: "🇨🇭", tel: "+41", para: "CHF",
        sehirler: ["Basel", "Bern (Başkent)", "Biel/Bienne", "Chur", "Emmen", "Fribourg", "Geneva (Cenevre)", "Kreuzlingen", "Köniz", "La Chaux-de-Fonds", "Lancy", "Lausanne", "Liestal", "Lucerne (Luzern)", "Lugano", "Montreux", "Neuchâtel", "Schaffhausen", "Sion", "St. Gallen", "Thun", "Uster", "Vernier", "Winterthur", "Zürich (Zürih)"]
    },
    "IT": { 
        isim: "İtalya", bayrak: "🇮🇹", tel: "+39", para: "EUR",
        sehirler: ["Bari", "Bergamo", "Bologna", "Brescia", "Cagliari", "Catania", "Ferrara", "Firenze (Floransa)", "Foggia", "Forlì", "Genua (Cenova)", "Giugliano in Campania", "Latina", "Livorno", "Messina", "Milano", "Modena", "Monza", "Napoli", "Padova", "Palermo", "Parma", "Perugia", "Pescara", "Prato", "Ravenna", "Reggio Calabria", "Reggio Emilia", "Rimini", "Roma (Roma) – Başkent", "Salerno", "Sassari", "Siracusa", "Taranto", "Terni", "Torino", "Trento", "Trieste", "Venezia (Venedik)", "Verona", "Vicenza"]
    },
    "LV": { 
        isim: "Letonya", bayrak: "🇱🇻", tel: "+371", para: "EUR",
        sehirler: ["Balvi", "Bauska", "Cēsis", "Daugavpils", "Gulbene", "Jelgava", "Jēkabpils", "Jūrmala", "Liepāja", "Ludza", "Madona", "Ogre", "Riga (Başkent)", "Rēzekne", "Sigulda", "Smiltene", "Talsi", "Tukums", "Valmiera", "Ventspils"]
    },
    "LT": { 
        isim: "Litvanya", bayrak: "🇱🇹", tel: "+370", para: "EUR",
        sehirler: ["Alytus", "Druskininkai", "Jonava", "Kaunas", "Klaipėda", "Kėdainiai", "Marijampolė", "Mažeikiai", "Palanga", "Panevėžys", "Plungė", "Rokiškis", "Tauragė", "Telšiai", "Ukmergė", "Utena", "Vilnius (Başkent)", "Visaginas", "Šiauliai", "Šilutė"]
    },
    "LU": { 
        isim: "Lüksemburg", bayrak: "🇱🇺", tel: "+352", para: "EUR",
        sehirler: ["Capellen", "Clervaux", "Diekirch", "Differdange", "Dudelange", "Echternach", "Esch-sur-Alzette", "Ettelbruck", "Grevenmacher", "Luxembourg (Başkent)", "Mersch", "Mondorf-les-Bains", "Remich", "Vianden", "Wiltz"]
    },
    "HU": { 
        isim: "Macaristan", bayrak: "🇭🇺", tel: "+36", para: "HUF",
        sehirler: ["Budapest (Başkent)", "Békéscsaba", "Debrecen", "Dunaújváros", "Eger", "Győr", "Hódmezővásárhely", "Kaposvár", "Kecskemét", "Miskolc", "Nagykanizsa", "Nyíregyháza", "Pécs", "Salgotarjan", "Sopron", "Szeged", "Szekszárd", "Székesfehérvár", "Szolnok", "Szombathely", "Tatabánya", "Veszprém", "Zalaegerszeg", "Érd"]
    },
    "MT": { 
        isim: "Malta", bayrak: "🇲🇹", tel: "+356", para: "EUR",
        sehirler: ["Balzan", "Birkirkara", "Birgu", "Birżebbuġa", "Bormla", "Cospicua", "Fgura", "Għargħur", "Kalkara", "Marsaskala", "Marsaxlokk", "Mdina", "Mellieħa", "Mosta", "Mtarfa", "Paola", "Qormi", "Rabat", "San Ġwann", "Siġġiewi", "Sliema", "St. Julian’s (San Ġiljan)", "Valletta (Başkent)", "Zurrieq", "Żabbar", "Żejtun", "Ħamrun"]
    },
    "NO": { 
        isim: "Norveç", bayrak: "🇳🇴", tel: "+47", para: "NOK",
        sehirler: ["Arendal", "Bergen", "Bodø", "Drammen", "Fredrikstad", "Gjøvik", "Halden", "Hamar", "Haugesund", "Kongsberg", "Kristiansand", "Larvik", "Lillehammer", "Molde", "Moss", "Oslo (Başkent)", "Sandefjord", "Sandnes", "Sarpsborg", "Skien", "Stavanger", "Tromsø", "Trondheim", "Tønsberg", "Ålesund"]
    },
    "PL": { 
        isim: "Polonya", bayrak: "🇵🇱", tel: "+48", para: "PLN",
        sehirler: ["Białystok", "Bielsko-Biała", "Bydgoszcz", "Częstochowa", "Elbląg", "Gdańsk", "Gdynia", "Gliwice", "Gorzów Wielkopolski", "Katowice", "Kielce", "Kraków (Krakow)", "Lublin", "Nowy Sącz", "Olsztyn", "Opole", "Poznań", "Płock", "Radom", "Ruda Śląska", "Rybnik", "Rzeszów", "Sosnowiec", "Szczecin", "Toruń", "Tychy", "Varşova (Warszawa) – Başkent", "Wałbrzych", "Wrocław", "Zabrze", "Zielona Góra", "Łódź"]
    },
    "PT": { 
        isim: "Portekiz", bayrak: "🇵🇹", tel: "+351", para: "EUR",
        sehirler: ["Amadora", "Aveiro", "Barcelos", "Beja", "Braga", "Caldas da Rainha", "Cascais", "Coimbra", "Covilhã", "Faro", "Funchal", "Guimarães", "Leiria", "Lisboa (Lizbon) – Başkent", "Loulé", "Matosinhos", "Odivelas", "Ponta Delgada", "Portimão", "Porto", "Santarem", "Seixal", "Setúbal", "Viana do Castelo", "Vila Nova de Gaia", "Viseu", "Évora"]
    },
    "RO": { 
        isim: "Romanya", bayrak: "🇷🇴", tel: "+40", para: "RON",
        sehirler: ["Alba Iulia", "Arad", "Bacău", "Baia Mare", "Bistrița", "Botoșani", "Brașov", "Brăila", "Buzău", "Bükreş (București) – Başkent", "Cluj-Napoca", "Constanța", "Craiova", "Drobeta-Turnu Severin", "Focșani", "Galați", "Iași", "Oradea", "Piatra Neamț", "Ploiești", "Râmnicu Vâlcea", "Satu Mare", "Sibiu", "Sighișoara", "Suceava", "Timișoara", "Tulcea", "Târgu Jiu", "Târgu Mureș"]
    },
    "SK": { 
        isim: "Slovakya", bayrak: "🇸🇰", tel: "+421", para: "EUR",
        sehirler: ["Banská Bystrica", "Bratislava (Başkent)", "Humenné", "Košice", "Levice", "Martin", "Michalovce", "Nitra", "Nové Zámky", "Piešťany", "Poprad", "Považská Bystrica", "Prešov", "Prievidza", "Spišská Nová Ves", "Trenčín", "Trnava", "Zvolen", "Šaľa", "Žilina"]
    },
    "SI": { 
        isim: "Slovenya", bayrak: "🇸🇮", tel: "+386", para: "EUR",
        sehirler: ["Bled", "Celje", "Izola", "Jesenice", "Kamnik", "Kočevje", "Koper", "Kranj", "Ljubljana (Başkent)", "Maribor", "Murska Sobota", "Nova Gorica", "Novo Mesto", "Ptuj", "Radovljica", "Slovenj Gradec", "Trbovlje", "Velenje", "Šempeter", "Škofja Loka"]
    },
    "TR": { 
        isim: "Türkiye", bayrak: "🇹🇷", tel: "+90", para: "TRY",
        sehirler: ["Adana", "Adıyaman", "Afyonkarahisar", "Aksaray", "Amasya", "Ankara", "Antalya", "Ardahan", "Artvin", "Aydın", "Ağrı", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Denizli", "Diyarbakır", "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "Kahramanmaraş", "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kilis", "Kocaeli", "Konya", "Kütahya", "Kırıkkale", "Kırklareli", "Kırşehir", "Malatya", "Manisa", "Mardin", "Mersin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat", "Zonguldak", "Çanakkale", "Çankırı", "Çorum", "İstanbul", "İzmir", "Şanlıurfa", "Şırnak"]
    },
    "GR": { 
        isim: "Yunanistan", bayrak: "🇬🇷", tel: "+30", para: "EUR",
        sehirler: ["Agrinio", "Alexandroupoli", "Argos", "Atina (Athens) – Başkent", "Chalcis (Evia)", "Chania", "Chios", "Corfu (Kerkyra)", "Drama", "Heraklion (Girit)", "Ioannina", "Kalamata", "Katerini", "Kavala", "Komotini", "Kozani", "Kozáni", "Larissa", "Mytilene (Lesbos)", "Nea Ionia", "Patras", "Preveza", "Rhodos", "Selanik (Thessaloniki)", "Serres", "Trikala", "Volos", "Xanthi"]
    }
};

// --- GITHUB & OPEN DATA KAYNAKLI ARAÇ LİSTESİ (ULTRA KAPSAMLI) ---
const arabaVeritabani = {
    "Abarth": ["124 Spider", "500", "500C", "595", "595C", "695", "695C", "Grande Punto", "Punto Evo", "Ritmo"],
    "AC": ["Ace", "Aceca", "Cobra"],
    "Acura": ["CL", "CSX", "EL", "ILX", "Integra", "Legend", "MDX", "NSX", "RDX", "RL", "RLX", "RSX", "SLX", "TL", "TLX", "TSX", "ZDX"],
    "Aiways": ["U5", "U6"],
    "Aixam": ["A.721", "A.741", "A.751", "City", "Coupe", "Crossline", "Crossover", "GTO", "Mega", "Minauto", "Scouty"],
    "Alfa Romeo": ["145", "146", "147", "155", "156", "159", "164", "166", "33", "4C", "6", "75", "8C Competizione", "90", "Alfasud", "Alfetta", "Arna", "Brera", "Giulia", "Giulietta", "GT", "GTV", "MiTo", "Montreal", "RZ", "Spider", "Stelvio", "SZ", "Tonale"],
    "Alpine": ["A110", "A310", "A610", "GTA", "V6"],
    "Aston Martin": ["Cygnet", "DB11", "DB7", "DB9", "DBS", "DBX", "Lagonda", "Rapide", "V12 Vantage", "V8 Vantage", "Vanquish", "Virage", "Vulcan", "Valkyrie", "One-77"],
    "Audi": ["100", "200", "50", "80", "90", "A1", "A2", "A3", "A4", "A4 Allroad", "A5", "A6", "A6 Allroad", "A7", "A8", "Cabriolet", "Coupe", "e-tron", "e-tron GT", "Q2", "Q3", "Q3 Sportback", "Q4 e-tron", "Q5", "Q5 Sportback", "Q7", "Q8", "Quattro", "R8", "RS Q3", "RS Q8", "RS2", "RS3", "RS4", "RS5", "RS6", "RS7", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "SQ2", "SQ5", "SQ7", "SQ8", "TT", "TT RS", "V8"],
    "Austin": ["Allegro", "Ambassador", "Maestro", "Maxi", "Metro", "Mini", "Montego", "Princess"],
    "Bentley": ["Arnage", "Azure", "Bentayga", "Brooklands", "Continental", "Continental Flying Spur", "Continental GT", "Continental GTC", "Eight", "Flying Spur", "Mulsanne", "Turbo R", "Turbo RT", "Turbo S"],
    "BMW": ["1 Serisi", "114", "116", "118", "120", "123", "125", "130", "135", "M135", "2 Serisi", "214", "216", "218", "220", "225", "228", "230", "M2", "M235", "M240", "3 Serisi", "315", "316", "318", "320", "323", "324", "325", "328", "330", "335", "340", "ActiveHybrid 3", "M3", "4 Serisi", "418", "420", "425", "428", "430", "435", "440", "M4", "5 Serisi", "518", "520", "523", "524", "525", "528", "530", "535", "540", "545", "550", "ActiveHybrid 5", "M5", "M550", "6 Serisi", "628", "630", "633", "635", "640", "645", "650", "M6", "7 Serisi", "725", "728", "730", "732", "735", "740", "745", "750", "760", "ActiveHybrid 7", "8 Serisi", "840", "850", "M8", "i3", "i4", "i7", "i8", "iX", "iX1", "iX3", "X1", "X2", "X3", "X3 M", "X4", "X4 M", "X5", "X5 M", "X6", "X6 M", "X7", "XM", "Z1", "Z3", "Z4", "Z8"],
    "Bugatti": ["Chiron", "Divo", "EB 110", "Veyron"],
    "Buick": ["Century", "Electra", "Enclave", "LaCrosse", "Le Sabre", "Park Avenue", "Regal", "Riviera", "Roadmaster", "Skylark"],
    "BYD": ["Atto 3", "Dolphin", "Han", "Seal", "Tang", "E6", "Yuan Plus"],
    "Cadillac": ["Allante", "ATS", "BLS", "Brougham", "CT6", "CTS", "Catera", "Deville", "DTS", "Eldorado", "Escalade", "Fleetwood", "Seville", "SRX", "STS", "XLR", "XT4", "XT5", "XT6", "XTS"],
    "Caterham": ["Seven", "Super Seven"],
    "Chevrolet": ["Alero", "Astro", "Avalanche", "Aveo", "Beretta", "Blazer", "Camaro", "Captiva", "Cavalier", "Chevelle", "Chevy Van", "Citation", "Cobalt", "Colorado", "Corsica", "Corvette", "Cruze", "El Camino", "Epica", "Equinox", "Evanda", "Express", "G", "HHR", "Impala", "K1500", "K30", "Kalos", "Lacetti", "Lumina", "Malibu", "Matiz", "Monte Carlo", "Nubira", "Orlando", "Rezzo", "S-10", "Silverado", "Spark", "Suburban", "Tacuma", "Tahoe", "Tracker", "TrailBlazer", "Trans Sport", "Traverse", "Trax", "Volt"],
    "Chrysler": ["300C", "300M", "Crossfire", "Daytona", "Delta", "ES", "Grand Voyager", "GTS", "Le Baron", "Neon", "New Yorker", "Pacifica", "PT Cruiser", "Saratoga", "Sebring", "Stratus", "Viper", "Vision", "Voyager", "Ypsilon"],
    "Citroen": ["2 CV", "AMI", "AX", "Berlingo", "BX", "C-Crosser", "C-Elysee", "C-Zero", "C1", "C15", "C2", "C25", "C3", "C3 Aircross", "C3 Picasso", "C3 Pluriel", "C4", "C4 Aircross", "C4 Cactus", "C4 Picasso", "C4 SpaceTourer", "C4 X", "C5", "C5 Aircross", "C5 X", "C6", "C8", "CX", "DS", "DS3", "DS4", "DS5", "Dyane", "E-Mehari", "Evasion", "Grand C4 Picasso", "Grand C4 SpaceTourer", "GSA", "Jumper", "Jumpy", "LN", "Méhari", "Nemo", "Saxo", "SM", "SpaceTourer", "Visa", "Xantia", "XM", "Xsara", "Xsara Picasso", "ZX"],
    "Cupra": ["Ateca", "Born", "Formentor", "Leon"],
    "Dacia": ["1300", "1310", "Dokker", "Duster", "Jogger", "Lodgy", "Logan", "Nova", "Pick Up", "Sandero", "Solenza", "Spring", "Super Nova"],
    "Daewoo": ["Espero", "Evanda", "Kalos", "Korando", "Lacetti", "Lanos", "Leganza", "Matiz", "Musso", "Nexia", "Nubira", "Rezzo", "Tacuma", "Tico"],
    "Daihatsu": ["Applause", "Charade", "Charmant", "Copen", "Cuore", "Feroza", "Freeclimber", "Gran Move", "Hijet", "Materia", "Move", "Rocky", "Sirion", "Taft", "Terios", "Trevis", "Valera", "YRV"],
    "Dodge": ["Avenger", "Caliber", "Caravan", "Challenger", "Charger", "Dakota", "Dart", "Daytona", "Durango", "Grand Caravan", "Intrepid", "Journey", "Magnum", "Neon", "Nitro", "RAM", "Shadow", "Stealth", "Stratus", "Viper"],
    "DS Automobiles": ["DS 3", "DS 3 Crossback", "DS 4", "DS 4 Crossback", "DS 5", "DS 7 Crossback", "DS 9"],
    "Ferrari": ["208", "246", "250", "296", "308", "328", "348", "360", "400", "412", "456", "458", "488", "512", "550", "575", "599 GTB", "612 Scaglietti", "812", "California", "Dino", "Enzo", "F12", "F355", "F40", "F430", "F50", "F512 M", "F8", "FF", "GTC4Lusso", "LaFerrari", "Mondial", "Portofino", "Roma", "SF90", "Superamerica", "Testarossa"],
    "Fiat": ["124 Spider", "124", "126", "127", "130", "131", "500", "500C", "500e", "500L", "500X", "600", "Albea", "Argenta", "Barchetta", "Brava", "Bravo", "Cinquecento", "Coupe", "Croma", "Dino", "Doblo", "Ducato", "Duna", "Fiorino", "Freemont", "Fullback", "Grande Punto", "Idea", "Linea", "Marea", "Marengo", "Multipla", "Palio", "Panda", "Punto", "Punto Evo", "Qubo", "Regata", "Ritmo", "Scudo", "Sedici", "Seicento", "Spider Europa", "Stilo", "Strada", "Talento", "Tempra", "Tipo", "Ulysse", "Uno", "X 1/9"],
    "Fisker": ["Karma", "Ocean"],
    "Ford": ["Aerostar", "B-Max", "Bronco", "C-Max", "Capri", "Cougar", "Courier", "Crown Victoria", "Econoline", "EcoSport", "Edge", "Escape", "Escort", "Excursion", "Expedition", "Explorer", "F 150", "F 250", "F 350", "Fairlane", "Falcon", "Fiesta", "Focus", "Fusion", "Galaxy", "Granada", "Grand C-Max", "Grand Tourneo Connect", "GT", "Ka/Ka+", "Kuga", "Maverick", "Mondeo", "Mustang", "Mustang Mach-E", "Orion", "Probe", "Puma", "Ranger", "S-Max", "Scorpio", "Sierra", "Streetka", "Taunus", "Taurus", "Thunderbird", "Tourneo Connect", "Tourneo Courier", "Tourneo Custom", "Transit", "Transit Connect", "Transit Courier", "Transit Custom", "Windstar"],
    "Genesis": ["G70", "G80", "G90", "GV60", "GV70", "GV80"],
    "GMC": ["Acadia", "Envoy", "Jimmy", "Safari", "Savana", "Sierra", "Sonoma", "Syclone", "Terrain", "Typhoon", "Vandura", "Yukon"],
    "Honda": ["Accord", "Civic", "Concerto", "CR-V", "CR-X", "CR-Z", "e", "Element", "FR-V", "HR-V", "Insight", "Integra", "Jazz", "Legend", "Logo", "NSX", "Odyssey", "Pilot", "Prelude", "Ridgeline", "S2000", "Shuttle", "Stream", "ZR-V"],
    "Hummer": ["H1", "H2", "H3"],
    "Hyundai": ["Accent", "Atos", "Bayon", "Coupe", "Elantra", "Excel", "Galloper", "Genesis", "Getz", "Grand Santa Fe", "Grandeur", "H-1", "H 100", "H 200", "H350", "i10", "i20", "i30", "i40", "Ioniq", "Ioniq 5", "Ioniq 6", "ix20", "ix35", "ix55", "Kona", "Lantra", "Matrix", "Nexo", "Pony", "S-Coupe", "Santa Fe", "Santamo", "Sonata", "Staria", "Terracan", "Trajet", "Tucson", "Veloster", "XG 30", "XG 350"],
    "Infiniti": ["EX30", "EX35", "EX37", "FX30", "FX35", "FX37", "FX45", "FX50", "G35", "G37", "J30", "M30", "M35", "M37", "M45", "Q30", "Q45", "Q50", "Q60", "Q70", "QX30", "QX50", "QX56", "QX60", "QX70"],
    "Isuzu": ["Campo", "D-Max", "Gemini", "Midi", "Pickup", "Trooper"],
    "Iveco": ["Daily", "Massif"],
    "Jaguar": ["Daimler", "E-Pace", "E-Type", "F-Pace", "F-Type", "I-Pace", "MK II", "S-Type", "X-Type", "XE", "XF", "XJ", "XJ12", "XJ40", "XJ6", "XJ8", "XJR", "XJS", "XK", "XK8", "XKR"],
    "Jeep": ["Avenger", "Cherokee", "CJ", "Commander", "Compass", "Gladiator", "Grand Cherokee", "Patriot", "Renegade", "Wagoneer", "Wrangler"],
    "Kia": ["Besta", "Carens", "Carnival", "Ceed", "Ceed SW", "Cerato", "Clarus", "EV6", "EV9", "Joice", "K2500", "K2700", "Leo", "Magentis", "Niro", "Opirus", "Optima", "Picanto", "Pregio", "Pride", "ProCeed", "Retona", "Rio", "Roadster", "Sephia", "Shuma", "Sorento", "Soul", "Spectra", "Sportage", "Stinger", "Stonic", "Venga", "XCeed"],
    "KTM": ["X-Bow"],
    "Lada": ["110", "111", "112", "1200", "2107", "Forma", "Granta", "Kalina", "Niva", "Nova", "Priora", "Samara", "Vesta", "XRAY"],
    "Lamborghini": ["Aventador", "Countach", "Diablo", "Espada", "Gallardo", "Huracan", "Jalpa", "LM002", "Miura", "Murcielago", "Urus"],
    "Lancia": ["Beta", "Dedra", "Delta", "Flaminia", "Flavia", "Fulvia", "Gamma", "Kappa", "Lybra", "Musa", "Phedra", "Prisma", "Thema", "Thesis", "Trevi", "Voyager", "Y", "Y10", "Ypsilon", "Zeta"],
    "Land Rover": ["Defender", "Discovery", "Discovery Sport", "Freelander", "Range Rover", "Range Rover Evoque", "Range Rover Sport", "Range Rover Velar", "Series I", "Series II", "Series III"],
    "Lexus": ["CT", "ES", "GS", "GX", "IS", "LC", "LFA", "LS", "LX", "NX", "RC", "RX", "RZ", "SC", "UX"],
    "Ligier": ["Ambra", "Be Two", "JS 50", "JS 60", "IXO", "Nova", "Optima", "X-Too"],
    "Lincoln": ["Aviator", "Continental", "LS", "Mark", "Navigator", "Town Car"],
    "Lotus": ["340R", "Cortina", "Elan", "Elise", "Elite", "Emira", "Esprit", "Europa", "Evora", "Exige", "Super Seven"],
    "Maserati": ["222", "224", "228", "3200", "4200", "422", "424", "430", "Biturbo", "Ghibli", "GranCabrio", "GranSport", "GranTurismo", "Grecale", "Indy", "Karif", "Levante", "MC20", "Merak", "Quattroporte", "Shamal", "Spyder"],
    "Maybach": ["57", "62"],
    "Mazda": ["121", "2", "3", "323", "5", "6", "626", "929", "B-Serisi", "BT-50", "CX-3", "CX-30", "CX-5", "CX-60", "CX-7", "CX-9", "Demio", "E-Serisi", "MPV", "MX-3", "MX-30", "MX-5", "MX-6", "Premacy", "RX-7", "RX-8", "Tribute", "Xedos 6", "Xedos 9"],
    "McLaren": ["540C", "570GT", "570S", "600LT", "650S", "675LT", "720S", "765LT", "Artura", "GT", "MP4-12C", "P1", "Senna"],
    "Mercedes-Benz": ["190", "200", "A-Serisi", "AMG GT", "B-Serisi", "C-Serisi", "Citan", "CL-Coupe", "CLA", "CLC", "CLK", "CLS", "E-Serisi", "EQA", "EQB", "EQC", "EQE", "EQS", "EQV", "G-Serisi", "GL-Serisi", "GLA", "GLB", "GLC", "GLE", "GLK", "GLS", "M-Serisi", "R-Serisi", "S-Serisi", "SL", "SLC", "SLK", "SLR McLaren", "SLS AMG", "Sprinter", "T-Serisi", "V-Serisi", "Vaneo", "Viano", "Vito", "X-Serisi"],
    "MG": ["EHS", "Marvel R", "MG ZS", "MG3", "MG4", "MG5", "MGF", "MGR", "TF", "ZR", "ZS", "ZT"],
    "Microcar": ["Due", "Flex", "M.GO", "M8", "MC1", "MC2", "Virgo"],
    "Mini": ["1000", "1300", "Cabrio", "Clubman", "Cooper", "Cooper S", "Countryman", "Coupe", "John Cooper Works", "One", "Paceman", "Roadster"],
    "Mitsubishi": ["3000 GT", "ASX", "Canter", "Carisma", "Colt", "Eclipse", "Eclipse Cross", "Galant", "Galloper", "Grandis", "i-MiEV", "L200", "L300", "L400", "Lancer", "Mirage", "Outlander", "Pajero", "Santamo", "Sapporo", "Sigma", "Space Gear", "Space Runner", "Space Star", "Space Wagon", "Starion", "Tredia"],
    "Morgan": ["3 Wheeler", "4/4", "Aero 8", "Plus 4", "Plus 8", "Roadster"],
    "Nissan": ["100 NX", "200 SX", "280 ZX", "300 ZX", "350Z", "370Z", "Almera", "Almera Tino", "Ariya", "Bluebird", "Cabstar", "Cube", "GT-R", "Interstar", "Juke", "King Cab", "Leaf", "Maxima", "Micra", "Murano", "Navara", "Note", "NP300", "NV200", "NV250", "NV300", "NV400", "Pathfinder", "Patrol", "PickUp", "Pixo", "Prairie", "Primastar", "Primera", "Pulsar", "Qashqai", "Qashqai+2", "Quest", "Serena", "Silvia", "Skyline", "Sunny", "Terrano", "Tiida", "Titan", "Townstar", "Trade", "Urvan", "Vanette", "X-Trail"],
    "Opel": ["Adam", "Admiral", "Agila", "Ampera", "Antara", "Arena", "Ascona", "Astra", "Calibra", "Campo", "Cascada", "Combo", "Commodore", "Corsa", "Crossland", "Crossland X", "Diplomat", "Frontera", "Grandland", "Grandland X", "GT", "Insignia", "Kadett", "Karl", "Manta", "Meriva", "Mokka", "Mokka X", "Monterey", "Monza", "Movano", "Omega", "Record", "Rocks-e", "Senator", "Signum", "Sintra", "Speedster", "Tigra", "Vectra", "Vivaro", "Zafira", "Zafira Life"],
    "Peugeot": ["1007", "104", "106", "107", "108", "2008", "204", "205", "206", "207", "208", "3008", "301", "304", "305", "306", "307", "308", "309", "4007", "4008", "404", "405", "406", "407", "408", "5008", "504", "505", "508", "604", "605", "607", "806", "807", "Bipper", "Boxer", "Expert", "iOn", "J5", "J9", "Partner", "RCZ", "Rifter", "Traveller"],
    "Polestar": ["1", "2", "3"],
    "Pontiac": ["Fiero", "Firebird", "Grand Am", "Grand Prix", "GTO", "Solstice", "Sunfire", "Trans Am", "Trans Sport"],
    "Porsche": ["356", "718 Boxster", "718 Cayman", "911", "912", "914", "918 Spyder", "924", "928", "944", "959", "968", "Boxster", "Carrera GT", "Cayenne", "Cayenne Coupe", "Cayman", "Macan", "Panamera", "Taycan"],
    "Renault": ["5", "19", "21", "25", "Alaskan", "Alpine", "Arkana", "Austral", "Avantime", "Captur", "Clio", "Espace", "Express", "Fluence", "Fuego", "Grand Espace", "Grand Modus", "Grand Scenic", "Kadjar", "Kangoo", "Koleos", "Laguna", "Latitude", "Master", "Megane", "Modus", "R 11", "R 14", "R 18", "R 19", "R 20", "R 21", "R 25", "R 30", "R 4", "R 5", "R 6", "R 9", "Rapid", "Safrane", "Scenic", "Spider", "Symbol", "Talisman", "Trafic", "Twingo", "Twizy", "Vel Satis", "Wind", "Zoe"],
    "Rolls-Royce": ["Camargue", "Corniche", "Cullinan", "Dawn", "Flying Spur", "Ghost", "Park Ward", "Phantom", "Silver Cloud", "Silver Dawn", "Silver Seraph", "Silver Shadow", "Silver Spirit", "Silver Spur", "Wraith"],
    "Rover": ["100", "200", "25", "400", "45", "600", "75", "800", "Maestro", "Mini", "Montego", "Streetwise"],
    "Saab": ["9-3", "9-5", "9-7X", "90", "900", "9000", "96", "99", "Sonett"],
    "Seat": ["Alhambra", "Altea", "Altea XL", "Arona", "Arosa", "Ateca", "Cordoba", "Exeo", "Fura", "Ibiza", "Inca", "Leon", "Malaga", "Marbella", "Mii", "Ronda", "Tarraco", "Terra", "Toledo"],
    "Skoda": ["105", "120", "130", "Citigo", "Enyaq", "Fabia", "Favorit", "Felicia", "Forman", "Kamiq", "Karoq", "Kodiaq", "Octavia", "Rapid", "Roomster", "Scala", "Superb", "Yeti"],
    "Smart": ["#1", "#3", "crossblade", "forfour", "fortwo", "Roadster"],
    "SsangYong": ["Actyon", "Family", "Korando", "Kyron", "Musso", "Rexton", "Rodius", "Tivoli", "XLV"],
    "Subaru": ["B9 Tribeca", "Baja", "BRZ", "Forester", "Impreza", "Justy", "Legacy", "Levorg", "Libero", "Outback", "Solterra", "SVX", "Trezia", "Tribeca", "Vivio", "WRX STI", "XV"],
    "Suzuki": ["Across", "Alto", "Baleno", "Cappuccino", "Carry", "Celerio", "Grand Vitara", "Ignis", "Jimny", "Kizashi", "Liana", "LJ 80", "Samurai", "S-Cross", "SJ 410", "SJ 413", "Splash", "Super-Carry", "Swace", "Swift", "SX4", "SX4 S-Cross", "Vitara", "Wagon R+", "X-90"],
    "Tesla": ["Model 3", "Model S", "Model X", "Model Y", "Roadster"],
    "Toyota": ["4-Runner", "Auris", "Avensis", "Avensis Verso", "Aygo", "Aygo X", "bZ4X", "Camry", "Carina", "Celica", "C-HR", "Corolla", "Corolla Cross", "Corolla Verso", "Cressida", "Crown", "Dyna", "FJ Cruiser", "GR86", "GT86", "Hiace", "Highlander", "Hilux", "IQ", "Land Cruiser", "Lite-Ace", "Mirai", "MR 2", "Paseo", "Picnic", "Previa", "Prius", "Prius+", "Proace", "Proace City", "Proace Verso", "RAV 4", "Sequoia", "Sienna", "Starlet", "Supra", "Tacoma", "Tercel", "Tundra", "Urban Cruiser", "Verso", "Verso-S", "Yaris", "Yaris Cross"],
    "Volkswagen": ["181", "Amarok", "Arteon", "Beetle", "Bora", "Buggy", "Caddy", "California", "Caravelle", "CC", "Corrado", "Crafter", "Eos", "Fox", "Golf", "Golf Plus", "Golf Sportsvan", "ID.3", "ID.4", "ID.5", "ID.Buzz", "Iltis", "Jetta", "Käfer", "Karmann Ghia", "Lupo", "Multivan", "New Beetle", "Passat", "Passat CC", "Phaeton", "Polo", "Santana", "Scirocco", "Sharan", "T-Cross", "T-Roc", "Taigo", "Taro", "Tiguan", "Tiguan Allspace", "Touareg", "Touran", "Transporter", "Up!", "Vento"],
    "Volvo": ["240", "244", "245", "262", "264", "340", "343", "344", "345", "360", "440", "460", "480", "740", "744", "745", "760", "780", "850", "855", "940", "944", "945", "960", "965", "Amazon", "C30", "C40", "C70", "P 121", "P 122", "P 1800", "Polar", "S40", "S60", "S70", "S80", "S90", "V40", "V50", "V60", "V70", "V90", "XC40", "XC60", "XC70", "XC90"]
};

// --- MARKET ZİNCİRLERİ VERİTABANI ---
const marketZincirleri = {
    "DE": {
        agregator: "https://www.kaufda.de",
        marketler: [
            { isim: "Lidl", brosur: "https://www.lidl.de/c/billiger-montag/a10006065", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Lidl-Logo.svg/200px-Lidl-Logo.svg.png" },
            { isim: "Aldi Süd", brosur: "https://www.aldi-sued.de/de/angebote.html", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/Aldi_S%C3%BCd_2017_logo.svg/200px-Aldi_S%C3%BCd_2017_logo.svg.png" },
            { isim: "Aldi Nord", brosur: "https://www.aldi-nord.de/angebote.html", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/Aldi_Nord_Logo_2015.svg/200px-Aldi_Nord_Logo_2015.svg.png" },
            { isim: "Edeka", brosur: "https://www.edeka.de/eh/angebote.jsp", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Edeka-Logo.svg/200px-Edeka-Logo.svg.png" },
            { isim: "Rewe", brosur: "https://www.rewe.de/angebote/", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4a/REWE_logo.svg/200px-REWE_logo.svg.png" },
            { isim: "Kaufland", brosur: "https://www.kaufland.de/angebote/aktuelle-woche.html", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Kaufland_logo.svg/200px-Kaufland_logo.svg.png" },
            { isim: "Penny", brosur: "https://www.penny.de/angebote", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/8/88/Penny_logo.svg/200px-Penny_logo.svg.png" },
            { isim: "Netto", brosur: "https://www.netto-online.de/angebote", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Netto_logo.svg/200px-Netto_logo.svg.png" },
            { isim: "Real", brosur: "https://www.real.de/angebote/", logo: "" },
            { isim: "Rossmann", brosur: "https://www.rossmann.de/de/angebote", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/9/95/Rossmann_Logo.svg/200px-Rossmann_Logo.svg.png" },
            { isim: "dm", brosur: "https://www.dm.de/tipps-und-trends/angebote", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b3/Dm-drogerie_markt.svg/200px-Dm-drogerie_markt.svg.png" }
        ]
    },
    "AT": {
        agregator: "https://www.wogibtswas.at",
        marketler: [
            { isim: "Billa", brosur: "https://www.billa.at/angebote", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Billa_Logo.svg/200px-Billa_Logo.svg.png" },
            { isim: "Spar", brosur: "https://www.spar.at/angebote", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Spar-Logo.svg/200px-Spar-Logo.svg.png" },
            { isim: "Hofer", brosur: "https://www.hofer.at/de/angebote.html", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Hofer_Logo.svg/200px-Hofer_Logo.svg.png" },
            { isim: "Lidl", brosur: "https://www.lidl.at/c/aktuell-im-angebot/a10006065", logo: "" },
            { isim: "Penny", brosur: "https://www.penny.at/angebote", logo: "" }
        ]
    },
    "BE": {
        agregator: "https://www.folder.be",
        marketler: [
            { isim: "Carrefour", brosur: "https://www.carrefour.be/fr/promotions", logo: "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Carrefour_logo.svg/200px-Carrefour_logo.svg.png" },
            { isim: "Delhaize", brosur: "https://www.delhaize.be/fr-be/promotions", logo: "" },
            { isim: "Colruyt", brosur: "https://www.colruyt.be/fr/depliants?folder=depliant", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.be/q/fr-BE/promotions", logo: "" },
            { isim: "Aldi", brosur: "https://www.aldi.be/fr/nos-depliants.html", logo: "" }
        ]
    },
    "BG": {
        agregator: "https://www.tiendeo.bg",
        marketler: [
            { isim: "Lidl", brosur: "https://www.lidl.bg/c/akcii/a10006065", logo: "" },
            { isim: "Kaufland", brosur: "https://www.kaufland.bg/aktualni-predlozheniya/ot-ponedelnik.html", logo: "" },
            { isim: "Billa", brosur: "https://www.billa.bg/oferti", logo: "" }
        ]
    },
    "CZ": {
        agregator: "https://www.tiendeo.cz",
        marketler: [
            { isim: "Lidl", brosur: "https://www.lidl.cz/c/akce-a-nabidky/a10006065", logo: "" },
            { isim: "Kaufland", brosur: "https://www.kaufland.cz/aktualni-nabidka/tento-tyden.html", logo: "" },
            { isim: "Albert", brosur: "https://www.albert.cz/nabidka-tyden", logo: "" },
            { isim: "Billa", brosur: "https://www.billa.cz/akce-a-slevy", logo: "" },
            { isim: "Penny", brosur: "https://www.penny.cz/nabidky", logo: "" }
        ]
    },
    "DK": {
        agregator: "https://www.tilbudsavis.dk",
        marketler: [
            { isim: "Netto", brosur: "https://netto.dk/tilbudsavis/", logo: "" },
            { isim: "Føtex", brosur: "https://foetex.dk/tilbudsavis/", logo: "" },
            { isim: "Bilka", brosur: "https://bilka.dk/tilbudsavis/", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.dk/c/tilbud/a10006065", logo: "" },
            { isim: "Aldi", brosur: "https://www.aldi.dk/tilbud.html", logo: "" }
        ]
    },
    "EE": {
        agregator: "https://www.tiendeo.ee",
        marketler: [
            { isim: "Rimi", brosur: "https://www.rimi.ee/e-pood/sooduspakkumised", logo: "" },
            { isim: "Maxima", brosur: "https://www.maxima.ee/pakkumised", logo: "" },
            { isim: "Selver", brosur: "https://www.selver.ee/sooduspakkumised", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.ee/c/pakkumised/a10006065", logo: "" }
        ]
    },
    "FI": {
        agregator: "https://www.tiendeo.fi",
        marketler: [
            { isim: "S-Market", brosur: "https://www.s-kaupat.fi/tarjoukset", logo: "" },
            { isim: "K-Market", brosur: "https://www.k-ruoka.fi/tarjoukset", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.fi/c/tarjoukset/a10006065", logo: "" },
            { isim: "Prisma", brosur: "https://www.prisma.fi/fi/tarjoukset", logo: "" }
        ]
    },
    "FR": {
        agregator: "https://www.bonial.fr",
        marketler: [
            { isim: "Carrefour", brosur: "https://www.carrefour.fr/promotions", logo: "" },
            { isim: "Leclerc", brosur: "https://www.e.leclerc/promotions", logo: "" },
            { isim: "Auchan", brosur: "https://www.auchan.fr/offres-et-promos", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.fr/nos-offres", logo: "" },
            { isim: "Intermarché", brosur: "https://www.intermarche.com/promotions", logo: "" }
        ]
    },
    "HR": {
        agregator: "https://www.tiendeo.hr",
        marketler: [
            { isim: "Lidl", brosur: "https://www.lidl.hr/c/akcije/a10006065", logo: "" },
            { isim: "Kaufland", brosur: "https://www.kaufland.hr/aktualna-ponuda/ovaj-tjedan.html", logo: "" },
            { isim: "Konzum", brosur: "https://www.konzum.hr/akcije", logo: "" },
            { isim: "Spar", brosur: "https://www.spar.hr/ponude", logo: "" }
        ]
    },
    "NL": {
        agregator: "https://www.reclamefolder.nl",
        marketler: [
            { isim: "Albert Heijn", brosur: "https://www.ah.nl/bonus", logo: "" },
            { isim: "Jumbo", brosur: "https://www.jumbo.com/aanbiedingen", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.nl/q/nl-NL/aanbiedingen", logo: "" },
            { isim: "Aldi", brosur: "https://www.aldi.nl/aanbiedingen.html", logo: "" },
            { isim: "Plus", brosur: "https://www.plus.nl/aanbiedingen", logo: "" }
        ]
    },
    "GB": {
        agregator: "https://www.tiendeo.co.uk",
        marketler: [
            { isim: "Tesco", brosur: "https://www.tesco.com/groceries/en-GB/promotions/alloffers", logo: "" },
            { isim: "Sainsbury's", brosur: "https://www.sainsburys.co.uk/gol-ui/groceries/offers", logo: "" },
            { isim: "Asda", brosur: "https://groceries.asda.com/special-offers", logo: "" },
            { isim: "Morrisons", brosur: "https://groceries.morrisons.com/offers", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.co.uk/offers", logo: "" },
            { isim: "Aldi", brosur: "https://www.aldi.co.uk/offers", logo: "" }
        ]
    },
    "IE": {
        agregator: "https://www.tiendeo.ie",
        marketler: [
            { isim: "Tesco", brosur: "https://www.tesco.ie/groceries/en-IE/promotions/alloffers", logo: "" },
            { isim: "Dunnes", brosur: "https://www.dunnesstoresgrocery.com/offers", logo: "" },
            { isim: "SuperValu", brosur: "https://supervalu.ie/real-rewards/offers", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.ie/offers", logo: "" },
            { isim: "Aldi", brosur: "https://www.aldi.ie/offers", logo: "" }
        ]
    },
    "ES": {
        agregator: "https://www.tiendeo.com/es",
        marketler: [
            { isim: "Mercadona", brosur: "https://www.mercadona.es/", logo: "" },
            { isim: "Carrefour", brosur: "https://www.carrefour.es/supermercado/ofertas/", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.es/es/nuestras-ofertas", logo: "" },
            { isim: "Dia", brosur: "https://www.dia.es/ofertas", logo: "" },
            { isim: "Eroski", brosur: "https://www.eroski.es/ofertas/", logo: "" }
        ]
    },
    "SE": {
        agregator: "https://www.tiendeo.se",
        marketler: [
            { isim: "ICA", brosur: "https://www.ica.se/erbjudanden/", logo: "" },
            { isim: "Coop", brosur: "https://www.coop.se/erbjudanden/", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.se/c/erbjudanden/a10006065", logo: "" },
            { isim: "Willys", brosur: "https://www.willys.se/erbjudanden", logo: "" }
        ]
    },
    "CH": {
        agregator: "https://www.tiendeo.ch",
        marketler: [
            { isim: "Migros", brosur: "https://www.migros.ch/de/aktionen.html", logo: "" },
            { isim: "Coop", brosur: "https://www.coop.ch/de/aktionen.html", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.ch/de/angebote", logo: "" },
            { isim: "Aldi", brosur: "https://www.aldi-suisse.ch/de/angebote.html", logo: "" },
            { isim: "Denner", brosur: "https://www.denner.ch/de/aktuell/", logo: "" }
        ]
    },
    "IT": {
        agregator: "https://www.tiendeo.it",
        marketler: [
            { isim: "Coop", brosur: "https://www.e-coop.it/offerte", logo: "" },
            { isim: "Conad", brosur: "https://www.conad.it/promozioni.html", logo: "" },
            { isim: "Esselunga", brosur: "https://www.esselunga.it/cms/promozioni.html", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.it/c/offerte/a10006065", logo: "" },
            { isim: "Carrefour", brosur: "https://www.carrefour.it/offerte", logo: "" }
        ]
    },
    "LV": {
        agregator: "https://www.tiendeo.lv",
        marketler: [
            { isim: "Rimi", brosur: "https://www.rimi.lv/e-veikals/lv/akcijas", logo: "" },
            { isim: "Maxima", brosur: "https://www.maxima.lv/akcijas", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.lv/c/piedavajumi/a10006065", logo: "" }
        ]
    },
    "LT": {
        agregator: "https://www.tiendeo.lt",
        marketler: [
            { isim: "Maxima", brosur: "https://www.maxima.lt/akcijos", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.lt/c/pasiulymai/a10006065", logo: "" },
            { isim: "Rimi", brosur: "https://www.rimi.lt/e-parduotuve/lt/akcijos", logo: "" },
            { isim: "Iki", brosur: "https://www.iki.lt/akcijos/", logo: "" }
        ]
    },
    "LU": {
        agregator: "https://www.tiendeo.lu",
        marketler: [
            { isim: "Cactus", brosur: "https://www.cactus.lu/fr/promotions", logo: "" },
            { isim: "Delhaize", brosur: "https://www.delhaize.lu/fr-lu/promotions", logo: "" },
            { isim: "Aldi", brosur: "https://www.aldi.lu/fr/offres.html", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.lu/fr/nos-offres", logo: "" }
        ]
    },
    "HU": {
        agregator: "https://www.tiendeo.hu",
        marketler: [
            { isim: "Lidl", brosur: "https://www.lidl.hu/c/akciok/a10006065", logo: "" },
            { isim: "Aldi", brosur: "https://www.aldi.hu/hu/ajanlatok.html", logo: "" },
            { isim: "Tesco", brosur: "https://tesco.hu/akciok/", logo: "" },
            { isim: "Spar", brosur: "https://www.spar.hu/akciok/akcios-ujsag", logo: "" },
            { isim: "Penny", brosur: "https://www.penny.hu/akciok", logo: "" }
        ]
    },
    "MT": {
        agregator: "https://www.tiendeo.com",
        marketler: [
            { isim: "Lidl", brosur: "https://www.lidl.com.mt/c/offers/a10006065", logo: "" },
            { isim: "Pavi", brosur: "https://www.pavi.com.mt/offers", logo: "" },
            { isim: "Scott's", brosur: "https://www.scotts.com.mt/", logo: "" }
        ]
    },
    "NO": {
        agregator: "https://www.tiendeo.no",
        marketler: [
            { isim: "Rema 1000", brosur: "https://www.rema.no/tilbud/", logo: "" },
            { isim: "Kiwi", brosur: "https://kiwi.no/tilbud/", logo: "" },
            { isim: "Coop", brosur: "https://coop.no/tilbud/", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.no/c/tilbud/a10006065", logo: "" }
        ]
    },
    "PL": {
        agregator: "https://www.tiendeo.pl",
        marketler: [
            { isim: "Biedronka", brosur: "https://www.biedronka.pl/pl/gazetki", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.pl/c/gazetka/a10006065", logo: "" },
            { isim: "Aldi", brosur: "https://www.aldi.pl/oferty.html", logo: "" },
            { isim: "Carrefour", brosur: "https://www.carrefour.pl/promocje", logo: "" },
            { isim: "Kaufland", brosur: "https://www.kaufland.pl/oferta-tygodnia/aktualny-tydzien.html", logo: "" }
        ]
    },
    "PT": {
        agregator: "https://www.tiendeo.pt",
        marketler: [
            { isim: "Continente", brosur: "https://www.continente.pt/campanhas/", logo: "" },
            { isim: "Pingo Doce", brosur: "https://www.pingodoce.pt/folhetos/", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.pt/c/ofertas/a10006065", logo: "" },
            { isim: "Aldi", brosur: "https://www.aldi.pt/ofertas.html", logo: "" }
        ]
    },
    "RO": {
        agregator: "https://www.tiendeo.ro",
        marketler: [
            { isim: "Lidl", brosur: "https://www.lidl.ro/c/oferte/a10006065", logo: "" },
            { isim: "Kaufland", brosur: "https://www.kaufland.ro/oferte/saptamana-curenta.html", logo: "" },
            { isim: "Carrefour", brosur: "https://www.carrefour.ro/promotii", logo: "" },
            { isim: "Mega Image", brosur: "https://www.mega-image.ro/promotii", logo: "" }
        ]
    },
    "SK": {
        agregator: "https://www.tiendeo.sk",
        marketler: [
            { isim: "Lidl", brosur: "https://www.lidl.sk/c/akcie/a10006065", logo: "" },
            { isim: "Kaufland", brosur: "https://www.kaufland.sk/aktualna-ponuka/tento-tyzden.html", logo: "" },
            { isim: "Billa", brosur: "https://www.billa.sk/akcie-a-novinky", logo: "" },
            { isim: "Tesco", brosur: "https://tesco.sk/akcie/", logo: "" }
        ]
    },
    "SI": {
        agregator: "https://www.tiendeo.si",
        marketler: [
            { isim: "Mercator", brosur: "https://www.mercator.si/aktualno/akcije/", logo: "" },
            { isim: "Lidl", brosur: "https://www.lidl.si/c/ponudbe/a10006065", logo: "" },
            { isim: "Spar", brosur: "https://www.spar.si/aktualno/akcije", logo: "" },
            { isim: "Hofer", brosur: "https://www.hofer.si/sl/ponudba.html", logo: "" }
        ]
    },
    "GR": {
        agregator: "https://www.tiendeo.gr",
        marketler: [
            { isim: "Lidl", brosur: "https://www.lidl.gr/c/prosfores/a10006065", logo: "" },
            { isim: "Sklavenitis", brosur: "https://www.sklavenitis.gr/prosfores/", logo: "" },
            { isim: "AB Vassilopoulos", brosur: "https://www.ab.gr/prosfores", logo: "" }
        ]
    },
    "TR": {
        agregator: "https://www.aktuelkatolog.com",
        marketler: [
            { isim: "BİM", brosur: "https://www.bim.com.tr/Categories/102/aktuel-urunler.aspx", logo: "" },
            { isim: "A101", brosur: "https://www.a101.com.tr/aktuel-urunler/", logo: "" },
            { isim: "ŞOK", brosur: "https://www.sokmarket.com.tr/aktuel-urunler", logo: "" },
            { isim: "Migros", brosur: "https://www.migros.com.tr/kampanyalar", logo: "" },
            { isim: "CarrefourSA", brosur: "https://www.carrefoursa.com/tr/kampanyalar", logo: "" }
        ]
    }
};

// --- ACİL YARDIM NUMARALARI VERİTABANI (30 ÜLKE) ---
const acilNumaralar = {
    "DE": {
        ulke: "Almanya",
        genelAcil: "112",
        polis: "110",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "ADAC", tel: "+49 89 22222222", aciklama: "Almanya'nın en büyük oto kulübü", turkce: false },
            { isim: "AVD", tel: "+49 69 6606-0", aciklama: "Alternatif yol yardım", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Berlin", tel: "+49 30 275850", adres: "Tiergartenstraße 19-21, Berlin" },
            { isim: "TR Başkonsolosluk Frankfurt", tel: "+49 69 71910", adres: "Baseler Str. 35-37, Frankfurt" },
            { isim: "TR Başkonsolosluk Münih", tel: "+49 89 17800", adres: "Denninger Str. 72, München" }
        ],
        ozelNotlar: "Otoyolda cep telefonu kullanımı yasaktır. Reflektif yelek zorunlu."
    },
    "AT": {
        ulke: "Avusturya",
        genelAcil: "112",
        polis: "133",
        ambulans: "144",
        yangin: "122",
        yolYardim: [
            { isim: "ÖAMTC", tel: "+43 120", aciklama: "Avusturya oto kulübü", turkce: false },
            { isim: "ARBÖ", tel: "+43 123", aciklama: "Alternatif yol yardım", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Viyana", tel: "+43 1 5052102", adres: "Prinz-Eugen-Str. 40, Wien" }
        ],
        ozelNotlar: "Vignette (otoyol çıkartması) zorunlu. Kış lastiği Kasım-Nisan arası mecburi."
    },
    "BE": {
        ulke: "Belçika",
        genelAcil: "112",
        polis: "101",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "Touring", tel: "+32 70 344777", aciklama: "Belçika oto kulübü", turkce: false },
            { isim: "VAB", tel: "+32 70 344777", aciklama: "Flemenkçe bölge", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Brüksel", tel: "+32 2 5130040", adres: "Rue Montoyer 4, Brussels" }
        ],
        ozelNotlar: "Üç resmi dil var: Fransızca, Flemenkçe, Almanca."
    },
    "BG": {
        ulke: "Bulgaristan",
        genelAcil: "112",
        polis: "166",
        ambulans: "150",
        yangin: "160",
        yolYardim: [
            { isim: "SBA", tel: "+359 2 9151", aciklama: "Bulgar oto birliği", turkce: false },
            { isim: "Roadside Assistance", tel: "+359 800 11 400", aciklama: "7/24 yol yardım", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Sofya", tel: "+359 2 9358500", adres: "Bul. Vasil Levski 80, Sofia" }
        ],
        ozelNotlar: "Vignette zorunlu. Sınır kapılarında uzun kuyruklar olabilir."
    },
    "CZ": {
        ulke: "Çekya",
        genelAcil: "112",
        polis: "158",
        ambulans: "155",
        yangin: "150",
        yolYardim: [
            { isim: "UAMK", tel: "+420 1230", aciklama: "Çek oto kulübü", turkce: false },
            { isim: "ABA", tel: "+420 1240", aciklama: "Alternatif yol yardım", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Prag", tel: "+420 224 311402", adres: "Pevnostní 1, Praha 6" }
        ],
        ozelNotlar: "Otoyol vignette zorunlu. Farlar gündüz de açık olmalı."
    },
    "DK": {
        ulke: "Danimarka",
        genelAcil: "112",
        polis: "114",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "FDM", tel: "+45 70 131313", aciklama: "Danimarka oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Kopenhag", tel: "+45 33 127100", adres: "Havnegade 21, København" }
        ],
        ozelNotlar: "Farlar 7/24 açık olmalı. Öresund köprüsü ücretli."
    },
    "EE": {
        ulke: "Estonya",
        genelAcil: "112",
        polis: "110",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "EAÜL", tel: "+372 6181881", aciklama: "Estonya oto birliği", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Tallinn", tel: "+372 6509400", adres: "Narva mnt 50, Tallinn" }
        ],
        ozelNotlar: "Kış lastiği Aralık-Mart arası zorunlu."
    },
    "FI": {
        ulke: "Finlandiya",
        genelAcil: "112",
        polis: "112",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "AL", tel: "+358 200 8080", aciklama: "Finlandiya oto birliği", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Helsinki", tel: "+358 9 6811030", adres: "Puistokatu 1, Helsinki" }
        ],
        ozelNotlar: "Kış lastiği Aralık-Şubat arası zorunlu. Geyik tehlikesi var."
    },
    "FR": {
        ulke: "Fransa",
        genelAcil: "112",
        polis: "17",
        ambulans: "15",
        yangin: "18",
        yolYardim: [
            { isim: "Autoroutes Emergency", tel: "SOS kabinleri", aciklama: "Otoyolda her 2 km'de SOS kabini", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Paris", tel: "+33 1 53924700", adres: "16 Avenue de Lamballe, Paris" },
            { isim: "TR Başkonsolosluk Lyon", tel: "+33 4 78896010", adres: "27 Rue Sébastien Gryphe, Lyon" }
        ],
        ozelNotlar: "Reflektif yelek ve üçgen zorunlu. Otoyollar ücretli."
    },
    "HR": {
        ulke: "Hırvatistan",
        genelAcil: "112",
        polis: "192",
        ambulans: "194",
        yangin: "193",
        yolYardim: [
            { isim: "HAK", tel: "+385 1 1987", aciklama: "Hırvat oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Zagreb", tel: "+385 1 4878280", adres: "Masarykova 3, Zagreb" }
        ],
        ozelNotlar: "Otoyollar ücretli. Farlar gündüz açık olmalı."
    },
    "NL": {
        ulke: "Hollanda",
        genelAcil: "112",
        polis: "0900-8844",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "ANWB", tel: "+31 88 2692888", aciklama: "Hollanda oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Lahey", tel: "+31 70 3604912", adres: "Jan Evertstraat 15, Den Haag" },
            { isim: "TR Başkonsolosluk Rotterdam", tel: "+31 10 4367424", adres: "Westblaak 172, Rotterdam" }
        ],
        ozelNotlar: "Bisikletlilere dikkat! Bisiklet yollarına park etmeyin."
    },
    "GB": {
        ulke: "İngiltere",
        genelAcil: "999",
        polis: "999",
        ambulans: "999",
        yangin: "999",
        yolYardim: [
            { isim: "AA", tel: "+44 800 887766", aciklama: "İngiliz oto kulübü", turkce: false },
            { isim: "RAC", tel: "+44 330 1597920", aciklama: "Alternatif yol yardım", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Londra", tel: "+44 20 73936202", adres: "43 Belgrave Square, London" }
        ],
        ozelNotlar: "Sol şerit trafiği! Brexit sonrası yeşil kart gerekebilir."
    },
    "IE": {
        ulke: "İrlanda",
        genelAcil: "112",
        polis: "999",
        ambulans: "999",
        yangin: "999",
        yolYardim: [
            { isim: "AA Ireland", tel: "+353 1 6179999", aciklama: "İrlanda oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Dublin", tel: "+353 1 6685240", adres: "11 Clyde Road, Dublin 4" }
        ],
        ozelNotlar: "Sol şerit trafiği! Kırsal yollar dar olabilir."
    },
    "ES": {
        ulke: "İspanya",
        genelAcil: "112",
        polis: "091",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "RACE", tel: "+34 900 100 992", aciklama: "İspanya oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Madrid", tel: "+34 91 3198064", adres: "Calle Rafael Calvo 18, Madrid" },
            { isim: "TR Başkonsolosluk Barcelona", tel: "+34 93 2178200", adres: "Paseo de la Bonanova 55, Barcelona" }
        ],
        ozelNotlar: "İki reflektif yelek zorunlu. Siesta saatlerinde dikkat."
    },
    "SE": {
        ulke: "İsveç",
        genelAcil: "112",
        polis: "114 14",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "Assistancekåren", tel: "+46 20 912912", aciklama: "İsveç yol yardım", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Stockholm", tel: "+46 8 21 8700", adres: "Östermalmsgatan 67, Stockholm" }
        ],
        ozelNotlar: "Farlar 7/24 açık olmalı. Geyik ve ren geyiği tehlikesi."
    },
    "CH": {
        ulke: "İsviçre",
        genelAcil: "112",
        polis: "117",
        ambulans: "144",
        yangin: "118",
        yolYardim: [
            { isim: "TCS", tel: "+41 800 140 140", aciklama: "İsviçre oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Bern", tel: "+41 31 3597070", adres: "Lombachweg 33, Bern" },
            { isim: "TR Başkonsolosluk Zürih", tel: "+41 44 2117930", adres: "Weinbergstr. 65, Zürich" }
        ],
        ozelNotlar: "Vignette zorunlu. Tünel geçişlerinde dikkat. Çok pahalı cezalar!"
    },
    "IT": {
        ulke: "İtalya",
        genelAcil: "112",
        polis: "113",
        ambulans: "118",
        yangin: "115",
        yolYardim: [
            { isim: "ACI", tel: "+39 803 116", aciklama: "İtalya oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Roma", tel: "+39 06 4469932", adres: "Piazza dei Quiriti 7, Roma" },
            { isim: "TR Başkonsolosluk Milano", tel: "+39 02 29519606", adres: "Via Monte di Pietà 17, Milano" }
        ],
        ozelNotlar: "ZTL (sınırlı trafik bölgesi) var. Otoyollar ücretli."
    },
    "LV": {
        ulke: "Letonya",
        genelAcil: "112",
        polis: "110",
        ambulans: "113",
        yangin: "112",
        yolYardim: [
            { isim: "LAMB", tel: "+371 67216222", aciklama: "Letonya oto birliği", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Riga", tel: "+371 67322654", adres: "Elizabetes iela 91, Riga" }
        ],
        ozelNotlar: "Kış lastiği Aralık-Mart zorunlu."
    },
    "LT": {
        ulke: "Litvanya",
        genelAcil: "112",
        polis: "112",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "LAS", tel: "+370 5 2616111", aciklama: "Litvanya oto birliği", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Vilnius", tel: "+370 5 2643584", adres: "Inžinerių g. 5, Vilnius" }
        ],
        ozelNotlar: "Farlar gündüz de açık olmalı."
    },
    "LU": {
        ulke: "Lüksemburg",
        genelAcil: "112",
        polis: "113",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "ACL", tel: "+352 26000", aciklama: "Lüksemburg oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Brüksel (kapsar)", tel: "+32 2 5130040", adres: "Brüksel üzerinden" }
        ],
        ozelNotlar: "Küçük ülke, trafik genelde rahat."
    },
    "HU": {
        ulke: "Macaristan",
        genelAcil: "112",
        polis: "107",
        ambulans: "104",
        yangin: "105",
        yolYardim: [
            { isim: "MAK", tel: "+36 1 3451717", aciklama: "Macar oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Budapeşte", tel: "+36 1 3449930", adres: "Andrássy út 123, Budapest" }
        ],
        ozelNotlar: "E-vignette zorunlu. Online alınabilir."
    },
    "MT": {
        ulke: "Malta",
        genelAcil: "112",
        polis: "112",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "Malta Motor Club", tel: "+356 21 237030", aciklama: "Malta oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Fahri Konsolosluk", tel: "+356 21 242900", adres: "Valletta" }
        ],
        ozelNotlar: "Sol şerit trafiği! Küçük ada, yollar dar."
    },
    "NO": {
        ulke: "Norveç",
        genelAcil: "112",
        polis: "112",
        ambulans: "113",
        yangin: "110",
        yolYardim: [
            { isim: "NAF", tel: "+47 08505", aciklama: "Norveç oto birliği", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Oslo", tel: "+47 22 122100", adres: "Drammensveien 84, Oslo" }
        ],
        ozelNotlar: "Çok pahalı cezalar! Tüneller yaygın. Kış lastiği zorunlu."
    },
    "PL": {
        ulke: "Polonya",
        genelAcil: "112",
        polis: "997",
        ambulans: "999",
        yangin: "998",
        yolYardim: [
            { isim: "PZM", tel: "+48 22 5191555", aciklama: "Polonya oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Varşova", tel: "+48 22 6210572", adres: "ul. Myśliwiecka 16, Warszawa" }
        ],
        ozelNotlar: "Farlar gündüz açık olmalı. Yol kalitesi değişken."
    },
    "PT": {
        ulke: "Portekiz",
        genelAcil: "112",
        polis: "112",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "ACP", tel: "+351 219 429 103", aciklama: "Portekiz oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Lizbon", tel: "+351 21 3954021", adres: "Av. das Descobertas 22, Lisboa" }
        ],
        ozelNotlar: "Otoyollar ücretli (elektronik). Fado dinle!"
    },
    "RO": {
        ulke: "Romanya",
        genelAcil: "112",
        polis: "112",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "ACR", tel: "+40 21 9222", aciklama: "Romanya oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Bükreş", tel: "+40 21 3030670", adres: "Calea Dorobanți 72, București" }
        ],
        ozelNotlar: "Vignette (Rovinieta) zorunlu. Yol kalitesi değişken."
    },
    "SK": {
        ulke: "Slovakya",
        genelAcil: "112",
        polis: "158",
        ambulans: "155",
        yangin: "150",
        yolYardim: [
            { isim: "SATC", tel: "+421 18 124", aciklama: "Slovak oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Bratislava", tel: "+421 2 54411691", adres: "Holubyho 11, Bratislava" }
        ],
        ozelNotlar: "E-vignette zorunlu. Kış lastiği Kasım-Mart."
    },
    "SI": {
        ulke: "Slovenya",
        genelAcil: "112",
        polis: "113",
        ambulans: "112",
        yangin: "112",
        yolYardim: [
            { isim: "AMZS", tel: "+386 1987", aciklama: "Slovenya oto birliği", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Ljubljana", tel: "+386 1 2005880", adres: "Verovškova 60, Ljubljana" }
        ],
        ozelNotlar: "Vignette zorunlu. Küçük ama güzel ülke."
    },
    "GR": {
        ulke: "Yunanistan",
        genelAcil: "112",
        polis: "100",
        ambulans: "166",
        yangin: "199",
        yolYardim: [
            { isim: "ELPA", tel: "+30 10400", aciklama: "Yunan oto kulübü", turkce: false }
        ],
        konsolosluk: [
            { isim: "TR Büyükelçilik Atina", tel: "+30 210 7245915", adres: "Vas. Georgiou B' 8, Athens" },
            { isim: "TR Başkonsolosluk Selanik", tel: "+30 2310 248490", adres: "Ag. Dimitriou 151, Thessaloniki" }
        ],
        ozelNotlar: "Ada feribotlarına dikkat. Yazın çok sıcak!"
    },
    "TR": {
        ulke: "Türkiye",
        genelAcil: "112",
        polis: "155",
        ambulans: "112",
        yangin: "110",
        yolYardim: [
            { isim: "TTOK", tel: "+90 212 282 81 40", aciklama: "Türkiye Turing", turkce: true },
            { isim: "Yol Yardım", tel: "0850 222 0 552", aciklama: "Sigorta şirketleri ortak", turkce: true }
        ],
        konsolosluk: [],
        ozelNotlar: "Eve hoş geldiniz! Sınır kapılarında yoğunluk olabilir."
    }
};

// Sorun tipleri listesi
const sorunTipleri = [
    { id: "araba_bozuldu", isim: "Araba Bozuldu", ikon: "fa-car-burst", renk: "orange" },
    { id: "kaza", isim: "Kaza Yaptım", ikon: "fa-car-crash", renk: "red" },
    { id: "lastik", isim: "Lastik Patladı", ikon: "fa-circle-xmark", renk: "yellow" },
    { id: "benzin", isim: "Benzin/Şarj Bitti", ikon: "fa-gas-pump", renk: "amber" },
    { id: "hirsizlik", isim: "Hırsızlık/Gasp", ikon: "fa-user-ninja", renk: "purple" },
    { id: "yangin", isim: "Yangın", ikon: "fa-fire", renk: "red" },
    { id: "saglik", isim: "Sağlık Sorunu", ikon: "fa-heart-pulse", renk: "pink" },
    { id: "diger", isim: "Diğer", ikon: "fa-circle-question", renk: "gray" }
];

// --- WAZE BENZERİ BİLDİRİM TÜRLERİ ---
const bildirimTurleri = [
    { 
        id: "radar", 
        isim: "Radar / Hız Kamerası", 
        ikon: "fa-camera", 
        renk: "#ef4444", // Kırmızı
        gecerlilikSaat: 24,
        emoji: "📸"
    },
    { 
        id: "kaza", 
        isim: "Kaza", 
        ikon: "fa-car-crash", 
        renk: "#f97316", // Turuncu
        gecerlilikSaat: 6,
        emoji: "💥"
    },
    { 
        id: "polis", 
        isim: "Polis Kontrolü", 
        ikon: "fa-user-shield", 
        renk: "#3b82f6", // Mavi
        gecerlilikSaat: 12,
        emoji: "👮"
    },
    { 
        id: "yol_calismasi", 
        isim: "Yol Çalışması", 
        ikon: "fa-road-barrier", 
        renk: "#eab308", // Sarı
        gecerlilikSaat: 168, // 7 gün
        emoji: "🚧"
    },
    { 
        id: "trafik", 
        isim: "Trafik Yoğunluğu", 
        ikon: "fa-traffic-light", 
        renk: "#a855f7", // Mor
        gecerlilikSaat: 2,
        emoji: "🚦"
    },
    { 
        id: "benzin", 
        isim: "Ucuz Benzin", 
        ikon: "fa-gas-pump", 
        renk: "#22c55e", // Yeşil
        gecerlilikSaat: 24,
        emoji: "⛽"
    },
    { 
        id: "mola", 
        isim: "İyi Mola Yeri", 
        ikon: "fa-mug-hot", 
        renk: "#78350f", // Kahve
        gecerlilikSaat: null, // Sürekli
        emoji: "☕"
    },
    { 
        id: "rusvet", 
        isim: "Rüşvet Uyarısı", 
        ikon: "fa-money-bill", 
        renk: "#ec4899", // Pembe
        gecerlilikSaat: 168, // 7 gün
        emoji: "💸"
    },
    { 
        id: "tehlike", 
        isim: "Yolda Tehlike", 
        ikon: "fa-triangle-exclamation", 
        renk: "#dc2626", // Koyu kırmızı
        gecerlilikSaat: 12,
        emoji: "⚠️"
    },
    { 
        id: "kapali_yol", 
        isim: "Kapalı Yol", 
        ikon: "fa-road-circle-xmark", 
        renk: "#991b1b", // Koyu kırmızı
        gecerlilikSaat: 168, // 7 gün
        emoji: "🚫"
    }
];

// Bildirim türü bilgisi getir
function getBildirimTuru(id) {
    return bildirimTurleri.find(t => t.id === id) || bildirimTurleri[bildirimTurleri.length - 1];
}

// Geçerlilik süresini hesapla
function hesaplaGecerlilik(bildirimTuruId) {
    const tur = getBildirimTuru(bildirimTuruId);
    if (!tur.gecerlilikSaat) return null; // Sürekli
    const now = new Date();
    return new Date(now.getTime() + tur.gecerlilikSaat * 60 * 60 * 1000);
}

// Market zincirlerini Supabase'e yüklemek için yardımcı fonksiyon
async function marketZincirleriniYukle() {
    if (!sb) {
        console.error('Supabase bağlantısı yok!');
        return;
    }
    
    const records = [];
    
    for (const [ulkeKod, ulkeData] of Object.entries(marketZincirleri)) {
        for (const market of ulkeData.marketler) {
            // Aynı market birden fazla ülkede olabilir, bu yüzden unique kontrolü yap
            const existingRecord = records.find(r => r.name === market.isim);
            
            if (existingRecord) {
                // Ülkeyi ekle
                if (!existingRecord.countries.includes(ulkeKod)) {
                    existingRecord.countries.push(ulkeKod);
                }
            } else {
                records.push({
                    name: market.isim,
                    logo_url: market.logo || null,
                    countries: [ulkeKod],
                    website: market.brosur.split('/').slice(0, 3).join('/'),
                    brochure_url: market.brosur
                });
            }
        }
    }
    
    console.log(`${records.length} market zinciri yüklenecek...`);
    
    // Batch insert
    const { data, error } = await sb.from('market_chains').upsert(records, { onConflict: 'name' });
    
    if (error) {
        console.error('Yükleme hatası:', error);
    } else {
        console.log('Market zincirleri başarıyla yüklendi!');
    }
}

// --- SİSTEM FONKSİYONLARI ---

// 1. Ülke Listesini Doldur (<select> içine)
function ulkeleriDoldur(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;
    
    // Önce temizle
    select.innerHTML = '<option value="">Ülke Seçiniz...</option>';

    // Alfabetik Sıralama
    const siraliKodlar = Object.keys(lokasyonVeritabani).sort((a, b) => 
        lokasyonVeritabani[a].isim.localeCompare(lokasyonVeritabani[b].isim, 'tr')
    );

    siraliKodlar.forEach(kod => {
        const ulke = lokasyonVeritabani[kod];
        let opt = document.createElement('option');
        opt.value = kod;
        opt.text = `${ulke.bayrak} ${ulke.isim}`;
        select.add(opt);
    });
}

// 2. Şehirleri Getir (Ülke Kodu verilince)
function sehirleriGetirOrtak(ulkeKod, sehirSelectId) {
    const sehirSelect = document.getElementById(sehirSelectId);
    if (!sehirSelect) return;

    // Önce temizle ve varsayılan seçeneği ekle
    sehirSelect.innerHTML = '<option value="">Şehir Seçiniz...</option>';
    
    if (ulkeKod && lokasyonVeritabani[ulkeKod]) {
        // Şehirleri alfabetik sırala
        const sehirler = lokasyonVeritabani[ulkeKod].sehirler.sort((a, b) => a.localeCompare(b, 'tr'));
        
        sehirler.forEach(sehir => {
            let opt = document.createElement('option');
            opt.value = sehir;
            opt.text = sehir;
            sehirSelect.add(opt);
        });
        
        // Kilidi aç
        sehirSelect.disabled = false;
        sehirSelect.classList.remove('opacity-50', 'cursor-not-allowed');
    } else {
        // Kilitli kalsın
        sehirSelect.disabled = true;
        sehirSelect.classList.add('opacity-50', 'cursor-not-allowed');
    }
}

// --- ZİYARETÇİ TAKİP SİSTEMİ ---

// 1. Sayfa Açılınca "Girdi" Diye Kaydet
document.addEventListener("DOMContentLoaded", async function() {
    // Sayfa adını bul (örn: market.html)
    let path = window.location.pathname;
    let page = path.split("/").pop() || "anasayfa"; 

    if(typeof sb !== 'undefined') {
        await sb.from('analytics').insert([
            { event_type: 'ziyaret', page_name: page, detail: 'Sayfa Görüntüleme' }
        ]);
        console.log("📡 Ziyaret kaydedildi:", page);
    }
});

// 2. Özel Aksiyonları Kaydetmek İçin Fonksiyon
async function logAction(actionName, detailText) {
    if(typeof sb !== 'undefined') {
        let path = window.location.pathname;
        let page = path.split("/").pop() || "anasayfa"; 
        
        await sb.from('analytics').insert([
            { event_type: 'aksiyon', page_name: page, detail: actionName + ': ' + detailText }
        ]);
    }
}

// Diğer sayfalardaki eski fonksiyon isimleriyle uyumluluk için takma adlar
const sehirleriGetir = sehirleriGetirOrtak;

// ============================================================================
// DÖVİZ VE ALTIN VERİLERİ
// ============================================================================

// Altın Türleri
const altinTurleri = [
    { id: "gram", isim: "Gram Altın", agirlik: 1.000, katsayi: 1.00, ikon: "fa-coins", renk: "#fbbf24" },
    { id: "ceyrek", isim: "Çeyrek Altın", agirlik: 1.750, katsayi: 1.03, ikon: "fa-circle", renk: "#f59e0b" },
    { id: "yarim", isim: "Yarım Altın", agirlik: 3.500, katsayi: 1.03, ikon: "fa-circle-half-stroke", renk: "#d97706" },
    { id: "tam", isim: "Tam Altın (Ata)", agirlik: 7.000, katsayi: 1.03, ikon: "fa-star", renk: "#b45309" },
    { id: "cumhuriyet", isim: "Cumhuriyet Altını", agirlik: 7.216, katsayi: 1.05, ikon: "fa-star-half-stroke", renk: "#92400e" },
    { id: "resat", isim: "Reşat Altını", agirlik: 7.200, katsayi: 1.08, ikon: "fa-crown", renk: "#78350f" },
    { id: "bilezik22", isim: "22 Ayar Bilezik (gr)", agirlik: 1.000, katsayi: 22/24, ikon: "fa-ring", renk: "#fcd34d" },
    { id: "bilezik18", isim: "18 Ayar Bilezik (gr)", agirlik: 1.000, katsayi: 18/24, ikon: "fa-ring", renk: "#fde68a" },
    { id: "bilezik14", isim: "14 Ayar Bilezik (gr)", agirlik: 1.000, katsayi: 14/24, ikon: "fa-ring", renk: "#fef3c7" }
];

// Para Birimleri (TL karşılıkları için)
const paraBirimleri = [
    // Ana Para Birimleri
    { kod: "EUR", isim: "Euro", sembol: "€", bayrak: "🇪🇺", ana: true },
    { kod: "USD", isim: "Amerikan Doları", sembol: "$", bayrak: "🇺🇸", ana: true },
    { kod: "GBP", isim: "İngiliz Sterlini", sembol: "£", bayrak: "🇬🇧", ana: true },
    { kod: "CHF", isim: "İsviçre Frangı", sembol: "CHF", bayrak: "🇨🇭", ana: true },
    
    // Avrupa Ülkeleri (Euro dışı)
    { kod: "SEK", isim: "İsveç Kronu", sembol: "kr", bayrak: "🇸🇪", ana: false },
    { kod: "NOK", isim: "Norveç Kronu", sembol: "kr", bayrak: "🇳🇴", ana: false },
    { kod: "DKK", isim: "Danimarka Kronu", sembol: "kr", bayrak: "🇩🇰", ana: false },
    { kod: "PLN", isim: "Polonya Zlotisi", sembol: "zł", bayrak: "🇵🇱", ana: false },
    { kod: "CZK", isim: "Çek Korunası", sembol: "Kč", bayrak: "🇨🇿", ana: false },
    { kod: "HUF", isim: "Macar Forinti", sembol: "Ft", bayrak: "🇭🇺", ana: false },
    { kod: "RON", isim: "Romen Leyi", sembol: "lei", bayrak: "🇷🇴", ana: false },
    { kod: "BGN", isim: "Bulgar Levası", sembol: "лв", bayrak: "🇧🇬", ana: false },
    { kod: "HRK", isim: "Hırvat Kunası", sembol: "kn", bayrak: "🇭🇷", ana: false },
    { kod: "RSD", isim: "Sırp Dinarı", sembol: "дин", bayrak: "🇷🇸", ana: false },
    { kod: "UAH", isim: "Ukrayna Grivnası", sembol: "₴", bayrak: "🇺🇦", ana: false },
    { kod: "RUB", isim: "Rus Rublesi", sembol: "₽", bayrak: "🇷🇺", ana: false },
    
    // Diğer Önemli Para Birimleri
    { kod: "TRY", isim: "Türk Lirası", sembol: "₺", bayrak: "🇹🇷", ana: false },
    { kod: "AZN", isim: "Azerbaycan Manatı", sembol: "₼", bayrak: "🇦🇿", ana: false },
    { kod: "GEL", isim: "Gürcü Larisi", sembol: "₾", bayrak: "🇬🇪", ana: false },
    { kod: "SAR", isim: "Suudi Riyali", sembol: "﷼", bayrak: "🇸🇦", ana: false },
    { kod: "AED", isim: "BAE Dirhemi", sembol: "د.إ", bayrak: "🇦🇪", ana: false },
    { kod: "QAR", isim: "Katar Riyali", sembol: "﷼", bayrak: "🇶🇦", ana: false },
    { kod: "KWD", isim: "Kuveyt Dinarı", sembol: "د.ك", bayrak: "🇰🇼", ana: false },
    { kod: "JPY", isim: "Japon Yeni", sembol: "¥", bayrak: "🇯🇵", ana: false },
    { kod: "CNY", isim: "Çin Yuanı", sembol: "¥", bayrak: "🇨🇳", ana: false },
    { kod: "AUD", isim: "Avustralya Doları", sembol: "$", bayrak: "🇦🇺", ana: false },
    { kod: "CAD", isim: "Kanada Doları", sembol: "$", bayrak: "🇨🇦", ana: false }
];

// Euro kullanan ülkeler
const euroZoneUlkeleri = ["DE", "AT", "BE", "FR", "NL", "ES", "IT", "PT", "GR", "IE", "FI", "EE", "LV", "LT", "SK", "SI", "MT", "CY", "LU", "HR"];

// Altın fiyatı hesaplama (gram fiyatından)
function hesaplaAltinFiyati(gramFiyat, altinTuruId) {
    const tur = altinTurleri.find(t => t.id === altinTuruId);
    if (!tur) return gramFiyat;
    return gramFiyat * tur.agirlik * tur.katsayi;
}

// Para birimi bilgisi getir
function getParaBirimi(kod) {
    return paraBirimleri.find(p => p.kod === kod) || { kod, isim: kod, sembol: kod, bayrak: "🏳️" };
}

// Tarayıcıda sayfaların global erişebilmesi için window'a bağla (const/let window'a eklenmez)
if (typeof window !== 'undefined') {
    window.lokasyonVeritabani = lokasyonVeritabani;
    window.acilNumaralar = acilNumaralar;
    window.sorunTipleri = sorunTipleri;
    window.marketZincirleri = marketZincirleri;
}