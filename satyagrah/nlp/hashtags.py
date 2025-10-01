# -*- coding: utf-8 -*-
def make_hashtags(topic: str = "judiciary", region: str = "india", lang: str = "en") -> str:
    lang = (lang or "en").lower()
    if lang == "hi":
        common = [
            "#भारत", "#समाचार", "#लोकतंत्र", "#राजनीति", "#दिल्ली", "#मुंबई", "#नयीदिल्ली"
        ]
        if topic == "judiciary":
            topic_tags = ["#न्यायपालिका", "#अदालत", "#कानून", "#सुनवाई", "#विचार"]
        else:
            topic_tags = [f"#{topic}"]
        if region == "india":
            region_tags = ["#इंडिया"]
        else:
            region_tags = [f"#{region}"]
        return " ".join(topic_tags + common + region_tags)
    # English (default)
    common = ["#dailybrief", "#civics", "#democracy", "#india", "#indiapolitics", "#delhi", "#mumbai", "#newdelhi"]
    if topic == "judiciary":
        topic_tags = ["#courtwatch", "#judicialreview", "#caseupdate", "#legalreform", "#courtroomsatire", "#politicalsatire"]
    else:
        topic_tags = [f"#{topic}", "#politicalsatire"]
    region_tags = ["#india"] if region == "india" else [f"#{region}"]
    return " ".join(topic_tags + common + region_tags)
