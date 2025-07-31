from rateMyProfessor.rateMyProfScrapper import RateMyProfAPI

prof = RateMyProfAPI(schoolId=1257, teacher="Jack Kolb")
prof.retrieveRMPInfo()
rating = prof.getRMPInfo()
Tags = prof.getTags()
retakeWithSameProf = prof.getWouldTakeAgain()

print(f"Rating: {rating}")
print(f"Tags: {Tags}")  
print(f"Would take again: {retakeWithSameProf}")

print("---------------another rmp scrapper website-------------------")