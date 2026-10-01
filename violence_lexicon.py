"""A curated French violence-related lexicon for thematic tracking.

Grouped into themes so you can SEE what drives the signal and defend/adjust it —
the whole point of a lexicon method in a humanities context. Terms are lemma forms
(lowercase) to match spaCy lemmas. Edit freely; `ALL` is derived automatically.

NOTE on ambiguity: a few words are polysemous in French (e.g. "arme" can appear in
"armes de la ville" heraldry; "lutte" can be metaphorical). Historical scouting
prose does use these literally most of the time, but treat the signal as thematic
PRESENCE of violence vocabulary, not a count of literal violent acts. Review
high-scoring issues by hand before drawing conclusions.
"""

WAR_COMBAT = {
    "guerre", "combat", "combattre", "bataille", "front", "offensive",
    "campagne", "conflit", "militaire", "soldat", "armée", "troupe",
    "mobilisation", "invasion", "occupation", "défense", "assaut",
}

PHYSICAL_VIOLENCE = {
    "violence", "violent", "frapper", "battre", "tuer", "mort", "mourir",
    "blesser", "blessure", "sang", "brutal", "brutalité", "coup", "massacre",
    "cruauté", "cruel", "souffrance", "douleur", "torture",
}

WEAPONS = {
    "arme", "fusil", "canon", "épée", "couteau", "poignard", "balle",
    "bombe", "explosif", "munition", "artillerie", "mitrailleuse", "baïonnette",
}

CONFLICT_AGGRESSION = {
    "ennemi", "attaque", "attaquer", "lutte", "lutter", "agression",
    "hostilité", "menace", "menacer", "haine", "révolte", "émeute",
    "danger", "péril", "destruction", "détruire", "ruine",
}

# Theme -> set, for grouped reporting.
THEMES = {
    "war_combat": WAR_COMBAT,
    "physical_violence": PHYSICAL_VIOLENCE,
    "weapons": WEAPONS,
    "conflict_aggression": CONFLICT_AGGRESSION,
}

# Flat set of every violence lemma.
ALL = set().union(*THEMES.values())
