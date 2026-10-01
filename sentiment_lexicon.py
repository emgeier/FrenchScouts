"""A small, transparent French sentiment lexicon for the PoC.

This is intentionally compact and editable — the point of a lexicon method is that
you can SEE and defend every word that drives a score, which matters in a
humanities context. For production you would swap in a published French lexicon
(e.g. FEEL, or NRC-FR) by replacing POSITIVE/NEGATIVE below with the loaded lists.
Or add your own keywords to track specific themes, such as violent imagery or nationalism.
Words are lemma forms (lowercase, no accents stripped) so they match spaCy lemmas.
"""

POSITIVE = {
    "aimer", "ami", "amitié", "amour", "beau", "beauté", "bien", "bon", "bonheur",
    "bonté", "brave", "charité", "confiance", "courage", "courageux", "dévouement",
    "digne", "espoir", "espérance", "fidèle", "fidélité", "fier", "fierté", "fort",
    "généreux", "générosité", "gloire", "grand", "harmonie", "heureux", "honneur",
    "honnête", "idéal", "joie", "joyeux", "juste", "justice", "liberté", "loyal",
    "loyauté", "lumière", "meilleur", "mérite", "noble", "paix", "parfait",
    "progrès", "pur", "pureté", "respect", "réussir", "sain", "service", "solidarité",
    "succès", "triomphe", "utile", "vaillant", "vertu", "victoire", "vrai", "zèle",
}

NEGATIVE = {
    "abandon", "affreux", "angoisse", "cruel", "cruauté", "danger", "défaite",
    "désastre", "désespoir", "détruire", "deuil", "difficile", "douleur", "dur",
    "échec", "ennemi", "faible", "faiblesse", "faute", "guerre", "haine", "honte",
    "horreur", "injuste", "injustice", "lâche", "lâcheté", "mal", "malheur",
    "malheureux", "mauvais", "mensonge", "menace", "méchant", "mépris", "misère",
    "mort", "mourir", "paresse", "pauvre", "pauvreté", "perdre", "péril", "peur",
    "pire", "ruine", "sang", "souffrance", "souffrir", "terreur", "trahir",
    "trahison", "triste", "tristesse", "vice", "violence", "violent",
}
