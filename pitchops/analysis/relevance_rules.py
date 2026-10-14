"""Free, conservative rule pre-filter for relevance (D3/D9). Pure. Anything uncertain goes to Gemini.

A video is rule-flagged irrelevant only when
  (a) its title names a non-UAE property market and NO UAE term appears anywhere, or
  (b) its title is team-culture / motivation / hiring content and NO property term appears anywhere.
"""

from __future__ import annotations

import re

UAE = re.compile(
    r"\b(dubai|abu\s?dhabi|sharjah|ajman|ras\s?al\s?khaimah|rak|umm\s?al\s?quwain|fujairah|uae|emirates|"
    r"jvc|jvt|jlt|jbr|business\s?bay|palm\s?jumeirah|jumeirah|marina|downtown\s?dubai|dubai\s?hills|creek|"
    r"damac|emaar|sobha|nakheel|aldar|meraas|azizi|danube|binghatti|ellington|deyaar|meydan|mbr\s?city|"
    r"arabian\s?ranches|dubai\s?south|al\s?barsha|yas|saadiyat|reem|golden\s?visa)\b|دبي|الإمارات|أبوظبي", re.I)
NON_UAE = re.compile(
    r"\b(london|manchester|birmingham|liverpool|bali|thailand|phuket|pattaya|bangkok|cyprus|limassol|turkey|"
    r"istanbul|antalya|portugal|lisbon|spain|marbella|georgia|tbilisi|batumi|pakistan|lahore|karachi|islamabad|"
    r"india|mumbai|pune|bangalore|bengaluru|hyderabad|kerala|kochi|gurgaon|noida|delhi|chennai|saudi|riyadh|"
    r"jeddah|oman|muscat|egypt|cairo|bahrain|manama|qatar|doha|miami|new\s?york|toronto|montenegro|greece|athens|"
    r"malaysia|kuala\s?lumpur|sri\s?lanka|colombo|maldives|mauritius|nigeria|lagos|kenya|nairobi|canada|australia|"
    r"sydney|melbourne)\b", re.I)
TEAM = re.compile(
    r"\b(birthday|office\s?party|team\s?building|award\s?night|awards?\s?ceremony|annual\s?party|we\s?are\s?hiring|"
    r"we'?re\s?hiring|hiring|join\s?our\s?team|motivation(al)?|iftar\s?(party|gathering)|eid\s?celebration|"
    r"christmas\s?party|diwali\s?celebration|team\s?outing|offsite|staff\s?party|anniversary\s?celebration|"
    r"national\s?day\s?celebration|women'?s\s?day)\b", re.I)
PROPERTY = re.compile(
    r"\b(apartment|apartments|villa|villas|propert(y|ies)|off[\s-]?plan|launch|project|investment|invest|for\s?sale|"
    r"rent(al)?|bedroom|\d\s?br|bhk|sq\.?\s?ft|sqft|price|aed|payment\s?plan|handover|roi|townhouse|penthouse|"
    r"studio|real\s?estate|mortgage|developer|community|tour)\b|عقار|شقة|فيلا", re.I)


def rule_irrelevant(title: str | None, description: str | None, tags: list[str] | None) -> str | None:
    """Returns a reason code when the video is clearly irrelevant, else None (= ask Gemini)."""
    t = title or ""
    everything = " ".join([t, description or "", " ".join(tags or [])])
    if NON_UAE.search(t) and not UAE.search(everything):
        return f"rule:non_uae_market:{NON_UAE.search(t).group(0).lower()}"  # type: ignore[union-attr]
    if TEAM.search(t) and not PROPERTY.search(everything):
        return f"rule:team_culture:{TEAM.search(t).group(0).lower()}"  # type: ignore[union-attr]
    return None
