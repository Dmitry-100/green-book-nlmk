"""Decision tree data for species identifier wizard."""

# Structure: each node has question_text, group, and either children (sub-questions) or species (leaf suggestions by name_latin)
DECISION_TREE = [
    # === PLANTS ===
    {
        "group": "plants",
        "question_text": "Где вы нашли растение?",
        "children": [
            {
                "question_text": "На обочине дороги или пустыре",
                "species": ["Artemisia vulgaris", "Artemisia absinthium", "Cirsium arvense", "Onopordum acanthium", "Plantago major", "Tanacetum vulgare", "Echium vulgare", "Lactuca serriola"]
            },
            {
                "question_text": "На газоне или лужайке",
                "species": ["Trifolium repens", "Poa annua", "Medicago lupulina", "Vicia cracca", "Linaria vulgaris"]
            },
            {
                "question_text": "Возле здания или забора",
                "species": ["Bassia scoparia", "Bromus squarrosus", "Anisantha tectorum", "Chamaenerion angustifolium"]
            },
            {
                "question_text": "Дерево или крупный кустарник",
                "species": ["Populus nigra", "Acer negundo", "Betula pendula", "Salix alba", "Robinia pseudoacacia"]
            },
        ]
    },
    # === FUNGI ===
    {
        "group": "fungi",
        "question_text": "Какого цвета шляпка гриба?",
        "children": [
            {
                "question_text": "Красная с белыми точками",
                "species": ["Amanita muscaria"]
            },
            {
                "question_text": "Зеленоватая или бледная",
                "species": ["Amanita phalloides"]
            },
            {
                "question_text": "Коричневая",
                "children": [
                    {
                        "question_text": "Шляпка воронковидная, край подвёрнут",
                        "species": ["Paxillus involutus"]
                    },
                    {
                        "question_text": "Шляпка выпуклая, ножка с чешуйками",
                        "species": ["Leccinum scabrum"]
                    },
                ]
            },
            {
                "question_text": "Яркая (красная, жёлтая, фиолетовая) без точек",
                "species": ["Russula sp."]
            },
        ]
    },
    # === INSECTS ===
    {
        "group": "insects",
        "question_text": "Какой тип насекомого?",
        "children": [
            {
                "question_text": "Бабочка",
                "species": ["Papilio machaon"]
            },
            {
                "question_text": "Жук",
                "species": ["Dytiscus latissimus"]
            },
            {
                "question_text": "Стрекоза",
                "species": ["Aeshna viridis"]
            },
            {
                "question_text": "Пчела или шмель",
                "species": ["Xylocopa valga"]
            },
        ]
    },
    # === HERPETOFAUNA ===
    {
        "group": "herpetofauna",
        "question_text": "Что вы видели?",
        "children": [
            {
                "question_text": "Ящерица",
                "species": ["Lacerta agilis"]
            },
            {
                "question_text": "Змея",
                "children": [
                    {
                        "question_text": "Жёлтые пятна на голове, неядовитая",
                        "species": ["Natrix natrix"]
                    },
                    {
                        "question_text": "Тёмная, без жёлтых пятен — ОСТОРОЖНО!",
                        "species": ["Vipera nikolskii"]
                    },
                ]
            },
            {
                "question_text": "Лягушка или жаба",
                "species": ["Pelophylax ridibundus"]
            },
        ]
    },
    # === BIRDS ===
    {
        "group": "birds",
        "question_text": "Где вы видели птицу?",
        "children": [
            {
                "question_text": "Возле зданий, на крышах, у столовой",
                "children": [
                    {
                        "question_text": "Голубь (серый, радужная шея)",
                        "species": ["Columba livia"]
                    },
                    {
                        "question_text": "Маленькая коричневая, чирикает",
                        "species": ["Passer domesticus"]
                    },
                    {
                        "question_text": "Чёрно-серая, крупная",
                        "species": ["Corvus cornix"]
                    },
                    {
                        "question_text": "Чёрно-белая с длинным хвостом",
                        "species": ["Pica pica"]
                    },
                    {
                        "question_text": "Маленькая с жёлтой грудкой",
                        "species": ["Parus major"]
                    },
                ]
            },
            {
                "question_text": "В воздухе, быстро летает",
                "children": [
                    {
                        "question_text": "Чёрная, серповидные крылья, не садится",
                        "species": ["Apus apus"]
                    },
                    {
                        "question_text": "Тёмная с блестящим оперением, стаями",
                        "species": ["Sturnus vulgaris"]
                    },
                ]
            },
            {
                "question_text": "В кустах или на деревьях",
                "children": [
                    {
                        "question_text": "Слышу характерное \"ку-ку\"",
                        "species": ["Cuculus canorus"]
                    },
                    {
                        "question_text": "Красиво поёт, вечером/ночью",
                        "species": ["Luscinia luscinia"]
                    },
                ]
            },
            {
                "question_text": "На воде или у водоёма",
                "children": [
                    {
                        "question_text": "Большая белая птица на воде",
                        "species": ["Cygnus olor"]
                    },
                    {
                        "question_text": "Крупная серая, длинные ноги",
                        "species": ["Grus grus"]
                    },
                ]
            },
        ]
    },
    # === MAMMALS ===
    {
        "group": "mammals",
        "question_text": "Какого размера животное?",
        "children": [
            {
                "question_text": "Маленькое (меньше кошки)",
                "children": [
                    {
                        "question_text": "Колючий шарик",
                        "species": ["Erinaceus europaeus"]
                    },
                    {
                        "question_text": "Маленький грызун, стоит столбиком",
                        "species": ["Spermophilus suslicus"]
                    },
                ]
            },
            {
                "question_text": "Среднее (размером с собаку)",
                "children": [
                    {
                        "question_text": "Длинные уши, прыгает",
                        "species": ["Lepus europaeus"]
                    },
                    {
                        "question_text": "Рыжая, пушистый хвост",
                        "species": ["Vulpes vulpes"]
                    },
                ]
            },
            {
                "question_text": "Крупное (больше собаки)",
                "children": [
                    {
                        "question_text": "Тёмное, массивное, клыки",
                        "species": ["Sus scrofa"]
                    },
                    {
                        "question_text": "Очень крупное, рога (лопатообразные)",
                        "species": ["Alces alces"]
                    },
                ]
            },
        ]
    },
]
