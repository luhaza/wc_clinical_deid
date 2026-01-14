from presidio_analyzer import PatternRecognizer, Pattern

# A collection of custom recognizers to be used by the AnalyzerEngines
# These are weak, to be updated later
# Medical Recognizer?
def get_titles_recognizer():
    titles_recognizer = PatternRecognizer(deny_list=["Mr.", "Mrs.", "Ms.", "Miss", "Dr.", "Prof.", "manager"],
                                          supported_entity="TITLE", name="TitlesRecognizer")
    return titles_recognizer

def get_location_deny_list():
    location_deny_list = PatternRecognizer(deny_list=["APO", "PSC", "AA", "Cyprus (Greek)", 
                                                      "ul", "AE", "DPO", "AP", "nan"],
                                          supported_entity="LOCATION", name="LocationDenylist")
    return location_deny_list

def get_age_recognizer():
    weak_regex= r"\b(110|[1-9]?[0-9])\b"
    age_pattern = Pattern(name="age (very weak)", 
                          regex=weak_regex, 
                          score=0.01)
    age_recognizer = PatternRecognizer(
        supported_entity="AGE",
        patterns = [age_pattern],
        name="AgeRecognizer",
        context=["month", "old", "turn", "age", "y/o"]
    )
    return age_recognizer

def get_zipcode_recognizer():
    weak_regex = r"\b\d{3,5}(?:-\d{3})?\b"
    med_regex = r"""
    (?:                           # Non-capturing group for matching
        (?:zip(?:code)?.{0,10})|  # Matches 'zip' or 'zipcode' with up to 10 non-alphanumeric characters
        (?:[A-Z]{2}\s)            # Matches a two-letter state acronym followed by a space
    )                             # End of non-capturing group
    (\d{3,7}(?:-\d{3})?)          # Captures 3 to 7 digits for the zip code, optionally followed by a dash and 3 more digits
    """ # weak regex pattern
    zipcode_pattern_weak = Pattern(name="zip code (weak)", regex=weak_regex, score=0.01)
    zipcode_pattern_med = Pattern(name="zip code (medium)", regex=med_regex, score=0.4)


    # Define the recognizer with the defined pattern
    zipcode_recognizer = PatternRecognizer(
        supported_entity="ZIP_CODE", 
        patterns=[zipcode_pattern_weak, zipcode_pattern_med], 
        name="ZipCodeRecognizer", 
        context=["zip", "zipcode"]
    )
    return zipcode_recognizer

recognizer_list = [get_titles_recognizer, get_location_deny_list, get_age_recognizer, get_zipcode_recognizer]
