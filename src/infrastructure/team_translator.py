class TeamTranslator:
    """Clase encargada de homogeneizar los nombres de los equipos entre Español (Mongo/API) e Inglés (CSV)."""
    
    _SPANISH_TO_ENGLISH = {
        "argentina": "Argentina",
        "argelia": "Algeria",
        "alemania": "Germany",
        "arabia saudita": "Saudi Arabia",
        "australia": "Australia",
        "bosnia": "Bosnia and Herzegovina",
        "bosnia y herzegovina": "Bosnia and Herzegovina",
        "belgica": "Belgium",
        "brasil": "Brazil",
        "canada": "Canada",
        "catar": "Qatar",
        "congo": "Congo",
        "rd congo": "Democratic Republic of the Congo",
        "republica democratica del congo": "Democratic Republic of the Congo",
        "corea del sur": "South Korea",
        "corea": "South Korea",
        "south korea": "South Korea",
        "korea republic": "South Korea",
        "costa de marfil": "Ivory Coast",
        "costa marfil": "Ivory Coast",
        "curazao": "Curaçao",
        "ecuador": "Ecuador",
        "egipto": "Egypt",
        "estados unidos": "United States",
        "eeuu": "United States",
        "francia": "France",
        "haiti": "Haiti",
        "iran": "Iran",
        "japon": "Japan",
        "marruecos": "Morocco",
        "mexico": "Mexico",
        "nueva zelanda": "New Zealand",
        "paises bajos": "Netherlands",
        "paraguay": "Paraguay",
        "republica checa": "Czech Republic",
        "korea checa": "Czech Republic", # Por si hay variantes de tipeo
        "senegal": "Senegal",
        "sudafrica": "South Africa",
        "south africa": "South Africa",
        "suecia": "Sweden",
        "suiza": "Switzerland",
        "tunez": "Tunisia",
        "turquia": "Turkey",
        "uruguay": "Uruguay",
        "uzbekistan": "Uzbekistan",
        "croacia": "Croatia",
        "inglaterra": "England",
        "portugal": "Portugal",
        "españa": "Spain",
        "espana": "Spain",
        "francia": "France",
        "ghana": "Ghana",
        "panama": "Panama",
        "polonia": "Poland",
        "dinamarca": "Denmark",
        "camerun": "Cameroon",
        "colombia": "Colombia",
        "peru": "Peru",
        "chile": "Chile",
        "venezuela": "Venezuela",
        "bolivia": "Bolivia",
        "gales": "Wales",
        "escocia": "Scotland",
        "austria": "Austria",
        "georgia": "Georgia",
        "rumania": "Romania",
        "eslovaquia": "Slovakia",
        "eslovenia": "Slovenia",
        "italia": "Italy",
        "ucrania": "Ukraine"
    }

    @classmethod
    def to_english(cls, team_name_es: str) -> str:
        """Convierte el nombre en español al nombre exacto del CSV. Si no existe, devuelve el original."""
        if not team_name_es:
            return ""
        # Limpiar espacios y pasar a minúsculas para evitar fallos por formato
        key = team_name_es.strip().lower()
        return cls._SPANISH_TO_ENGLISH.get(key, team_name_es.title())