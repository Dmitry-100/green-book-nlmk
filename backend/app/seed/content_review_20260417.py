"""Apply expert catalog corrections from the 2026-04-17 project review.

Usage:
    docker compose exec backend python -m app.seed.content_review_20260417
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.gamification import SpeciesFirstDiscovery
from app.models.observation import Observation
from app.models.species import Species, SpeciesCategory, SpeciesGroup

RED_BOOK_STATUS = "Красная книга Липецкой области"
BLUE_UNDERWING_PHOTO = "/api/media/species-pdf/page20_img06.png"


CATALOG_UPSERTS: list[dict[str, Any]] = [
    {
        "name_ru": "Ковыль перистый",
        "name_latin": "Stipa pennata",
        "group": "plants",
        "category": "red_book",
        "conservation_status": RED_BOOK_STATUS,
        "description": (
            "Многолетний степной злак с длинными перистыми остями. "
            "На промышленной площадке требует отдельного внимания как краснокнижный вид."
        ),
        "photo_urls": ["/api/media/species-pdf/page11_img00.png"],
    },
    {
        "name_ru": "Тополь черный",
        "name_latin": "Populus nigra",
        "group": "plants",
        "category": "typical",
        "description": "Крупное пойменное дерево, характерное для влажных участков и берегов водоёмов.",
    },
    {
        "name_ru": "Осина",
        "name_latin": "Populus tremula",
        "group": "plants",
        "category": "typical",
        "description": "Лиственное дерево с округлыми листьями на длинных черешках; обычна в светлых лесах и лесополосах.",
    },
    {
        "name_ru": "Рдест узловатый",
        "name_latin": "Potamogeton nodosus",
        "group": "plants",
        "category": "rare",
        "description": "Водное растение с плавающими листьями, встречающееся в реках и заводях с медленным течением.",
    },
    {
        "name_ru": "Плаун годичный",
        "name_latin": "Lycopodium annotinum",
        "group": "plants",
        "category": "rare",
        "description": "Вечнозелёное споровое растение влажных хвойных и смешанных лесов, чувствительное к вытаптыванию.",
    },
    {
        "name_ru": "Плаун булавовидный",
        "name_latin": "Lycopodium clavatum",
        "group": "plants",
        "category": "rare",
        "description": "Редкий плаун с ползучими побегами и булавовидными спороносными колосками.",
    },
    {
        "name_ru": "Рдест остролистный",
        "name_latin": "Potamogeton acutifolius",
        "group": "plants",
        "category": "red_book",
        "conservation_status": RED_BOOK_STATUS,
        "description": "Редкое водное растение чистых стоячих и слабопроточных водоёмов.",
    },
    {
        "name_ru": "Подосиновик",
        "name_latin": "Leccinum aurantiacum",
        "group": "fungi",
        "category": "typical",
        "description": "Трубчатый гриб с яркой шляпкой, чаще связанный с осинами и светлыми лиственными участками.",
    },
    {
        "name_ru": "Головач гигантский",
        "name_latin": "Calvatia gigantea",
        "group": "fungi",
        "category": "typical",
        "description": "Крупный шаровидный гриб лугов и опушек; молодые плодовые тела белые и плотные.",
    },
    {
        "name_ru": "Бабочка лимонница",
        "name_latin": "Gonepteryx rhamni",
        "group": "insects",
        "category": "typical",
        "description": "Одна из ранних весенних бабочек; самцы ярко-жёлтые, самки более светлые.",
    },
    {
        "name_ru": "Медведица госпожа",
        "name_latin": "Callimorpha dominula",
        "group": "insects",
        "category": "red_book",
        "conservation_status": RED_BOOK_STATUS,
        "description": "Яркая дневная медведица влажных лугов, опушек и зарослей у водоёмов.",
    },
    {
        "name_ru": "Голубянка аргирогномон",
        "name_latin": "Plebejus argyrognomon",
        "group": "insects",
        "category": "red_book",
        "conservation_status": RED_BOOK_STATUS,
        "description": "Небольшая голубянка открытых луговых местообитаний, чувствительная к зарастанию участков.",
    },
    {
        "name_ru": "Голубянка красивая",
        "name_latin": "Polyommatus bellargus",
        "group": "insects",
        "category": "red_book",
        "conservation_status": RED_BOOK_STATUS,
        "description": "Редкая голубянка сухих лугов и склонов; самцы отличаются насыщенно-голубой окраской крыльев.",
    },
    {
        "name_ru": "Медведица четырёхточечная",
        "name_latin": "Euplagia quadripunctaria",
        "group": "insects",
        "category": "red_book",
        "conservation_status": RED_BOOK_STATUS,
        "description": "Крупная яркая бабочка опушек и разнотравных участков, занесённая в региональные охранные списки.",
    },
    {
        "name_ru": "Голубая ленточница",
        "name_latin": "Catocala fraxini",
        "group": "insects",
        "category": "red_book",
        "conservation_status": RED_BOOK_STATUS,
        "description": "Крупная ночная бабочка с синими перевязями на задних крыльях.",
        "photo_urls": [BLUE_UNDERWING_PHOTO],
    },
    {
        "name_ru": "Мелангрия галатея",
        "name_latin": "Melanargia galathea",
        "group": "insects",
        "category": "red_book",
        "conservation_status": RED_BOOK_STATUS,
        "description": "Контрастная чёрно-белая бархатница лугов и опушек.",
        "photo_urls": ["/api/media/species-pdf/page20_img05.png"],
        "aliases": ["Галатея"],
    },
    {
        "name_ru": "Гадюка Никольского",
        "name_latin": "Vipera nikolskii",
        "group": "herpetofauna",
        "category": "typical",
        "is_poisonous": True,
        "conservation_status": None,
        "description": (
            "Тёмная ядовитая змея влажных местообитаний. При встрече не трогайте животное "
            "и сообщите экологу."
        ),
        "do_dont_rules": "Не приближайтесь и не пытайтесь поймать. Ядовита.",
        "photo_urls": ["/api/media/species-pdf/page21_img01.png"],
    },
    {
        "name_ru": "Грач",
        "name_latin": "Corvus frugilegus",
        "group": "birds",
        "category": "synanthropic",
        "description": "Общественная вороновая птица, обычная у населённых пунктов, полей и промышленных территорий.",
    },
    {
        "name_ru": "Большая выпь",
        "name_latin": "Botaurus stellaris",
        "group": "birds",
        "category": "red_book",
        "conservation_status": RED_BOOK_STATUS,
        "description": "Скрытная цаплевая птица тростниковых зарослей с характерным низким весенним голосом.",
    },
    {
        "name_ru": "Сокол сапсан",
        "name_latin": "Falco peregrinus",
        "group": "birds",
        "category": "red_book",
        "conservation_status": RED_BOOK_STATUS,
        "description": "Крупный сокол, известный стремительным пикирующим полётом во время охоты.",
    },
    {
        "name_ru": "Клинтух",
        "name_latin": "Columba oenas",
        "group": "birds",
        "category": "red_book",
        "conservation_status": RED_BOOK_STATUS,
        "description": "Лесной голубь, связанный со старыми дуплистыми деревьями и спокойными лесными участками.",
    },
    {
        "name_ru": "Серая неясыть",
        "name_latin": "Strix aluco",
        "group": "birds",
        "category": "red_book",
        "conservation_status": RED_BOOK_STATUS,
        "description": "Средняя сова старых лесов и парков, активная преимущественно ночью.",
    },
    {
        "name_ru": "Ёж обыкновенный",
        "name_latin": "Erinaceus europaeus",
        "group": "mammals",
        "category": "typical",
        "description": "Обычный насекомоядный зверёк опушек, садов и зарослей кустарника.",
    },
    {
        "name_ru": "Суслик европейский",
        "name_latin": "Spermophilus citellus",
        "group": "mammals",
        "category": "typical",
        "description": "Колониальный грызун открытых травянистых участков и сухих лугов.",
    },
    {
        "name_ru": "Заяц-беляк",
        "name_latin": "Lepus timidus",
        "group": "mammals",
        "category": "red_book",
        "conservation_status": RED_BOOK_STATUS,
        "description": "Лесной заяц, зимой меняющий окраску меха на белую.",
    },
]

CANONICAL_DUPLICATES = [
    ("Большая синица", "Синица"),
    ("Сорока", "Сорока обыкновенная"),
]

REMOVED_SPECIES_NAMES = [
    "Полынь горькая",
    "Крапчатый суслик",
    "Суслик крапчатый",
]

PHOTO_OVERRIDES = {
    "Малиновая ленточница": None,
    "Обыкновенный уж": None,
    "Уж обыкновенный": None,
}

PHOTO_UPDATES = {
    "Осина": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/Populus_tremula_001.jpg/960px-Populus_tremula_001.jpg",
    ],
    "Плаун булавовидный": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Lycopodium_clavatum_151207.jpg/960px-Lycopodium_clavatum_151207.jpg",
    ],
    "Плаун годичный": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Lycopodium_annotinum_161102a.jpg/960px-Lycopodium_annotinum_161102a.jpg",
    ],
    "Рдест остролистный": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/PotamogetonAcutifolius2.jpg/960px-PotamogetonAcutifolius2.jpg",
    ],
    "Рдест узловатый": [
        "https://upload.wikimedia.org/wikipedia/commons/c/c6/Potamogeton_nodosus_plant_%2801%29.jpg",
    ],
    "Тополь черный": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3d/Populus_nigra_%284999111186%29.jpg/960px-Populus_nigra_%284999111186%29.jpg",
    ],
    "Головач гигантский": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/92/Riesenbovist_Calvatia_gigantea.JPG/960px-Riesenbovist_Calvatia_gigantea.JPG",
    ],
    "Подосиновик": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Leccinum_aurantiacum.jpg/960px-Leccinum_aurantiacum.jpg",
    ],
    "Бабочка лимонница": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6a/Common_brimstone_butterfly_%28Gonepteryx_rhamni%29_male.jpg/960px-Common_brimstone_butterfly_%28Gonepteryx_rhamni%29_male.jpg",
    ],
    "Голубянка аргирогномон": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/%28MHNT%29_Plebejus_argyrognomon_-_Roztocze_Poland_-_male_dorsal.jpg/960px-%28MHNT%29_Plebejus_argyrognomon_-_Roztocze_Poland_-_male_dorsal.jpg",
    ],
    "Голубянка красивая": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/35/Polyommatus_bellargus_male%2C_Aveyron%2C_France_-_Diliff.jpg/960px-Polyommatus_bellargus_male%2C_Aveyron%2C_France_-_Diliff.jpg",
    ],
    "Малиновая ленточница": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c1/Catocala_sponsa.jpg/960px-Catocala_sponsa.jpg",
    ],
    "Медведица госпожа": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c2/20210521_Callimorpha_dominula_02.jpg/960px-20210521_Callimorpha_dominula_02.jpg",
    ],
    "Медведица четырёхточечная": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/e/eb/Russischer_B%C3%A4r_%28Euplagia_quadripunctaria%29_8056048-PSD.jpg/960px-Russischer_B%C3%A4r_%28Euplagia_quadripunctaria%29_8056048-PSD.jpg",
    ],
    "Обыкновенный уж": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d8/The_Grass_Snake_-_Natrix_natrix.jpg/960px-The_Grass_Snake_-_Natrix_natrix.jpg",
    ],
    "Большая выпь": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Rohrdommel_Flachsee.jpg/960px-Rohrdommel_Flachsee.jpg",
    ],
    "Грач": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Corvus_frugilegus%2C_Krak%C3%B3w%2C_20230225_0900_2882.jpg/960px-Corvus_frugilegus%2C_Krak%C3%B3w%2C_20230225_0900_2882.jpg",
    ],
    "Клинтух": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/2019-03-17_Columba_oenas%2C_Jesmond_Dene_1.jpg/960px-2019-03-17_Columba_oenas%2C_Jesmond_Dene_1.jpg",
    ],
    "Серая неясыть": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2b/Tawny_wiki_edit1.jpg/960px-Tawny_wiki_edit1.jpg",
    ],
    "Сокол сапсан": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Peregrine_falcon_%28Falco_peregrinus%29_in_flight%2C_Cape_Baily%2C_Kamay_Botany_Bay_NSW_Jun_2022.jpg/960px-Peregrine_falcon_%28Falco_peregrinus%29_in_flight%2C_Cape_Baily%2C_Kamay_Botany_Bay_NSW_Jun_2022.jpg",
    ],
    "Ёж обыкновенный": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cb/Erinaceus_europaeus_%28Linnaeus%2C_1758%29.jpg/960px-Erinaceus_europaeus_%28Linnaeus%2C_1758%29.jpg",
    ],
    "Заяц-беляк": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/5/53/Mountain_hare_%28Lepus_timidus%29_Oppdal.jpg/960px-Mountain_hare_%28Lepus_timidus%29_Oppdal.jpg",
    ],
    "Суслик европейский": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/European_souslik_%28Spermophilus_citellus%29_Obrovisko.jpg/960px-European_souslik_%28Spermophilus_citellus%29_Obrovisko.jpg",
    ],
}

LATIN_NAME_UPDATES = {
    "Синеголовник плосколистный": "Eryngium",
    "Гвоздика песчаная": "Dianthus",
    "Грушанка зеленоцветковая": "Pyrola",
    "Большое коромысло": "Aeshna",
    "Хейлозия Кузнецовой": "Cheilosia",
    "Болотная черепаха": "Emys orbicularis",
    "Гребенчатый тритон": "Triturus cristatus",
    "Живородящая ящерица": "Zootoca vivipara",
    "Ломкая веретеница": "Anguis fragilis",
    "Обыкновенная медянка": "Coronella austriaca",
    "Серая жаба": "Bufo bufo",
    "Травяная лягушка": "Rana temporaria",
    "Тритон обыкновенный": "Lissotriton vulgaris",
    "Узорчатый полоз": "Elaphe dione",
    "Чесночница": "Pelobates fuscus",
    "Балобан": "Falco cherrug",
    "Белоспинный дятел": "Dendrocopos leucotos",
    "Беркут": "Aquila chrysaetos",
    "Большая белая цапля": "Ardea alba",
    "Большой веретенник": "Limosa limosa",
    "Большой подорлик": "Clanga clanga",
    "Волчек (малая выпь)": "Ixobrychus minutus",
    "Галка": "Coloeus monedula",
    "Горлица": "Streptopelia turtur",
    "Длиннохвостая неясыть": "Strix uralensis",
    "Дупель": "Gallinago media",
    "Желна": "Dryocopus martius",
    "Змееяд": "Circaetus gallicus",
    "Козодой": "Caprimulgus europaeus",
    "Красношейная поганка": "Podiceps auritus",
    "Кулик-сорока": "Haematopus ostralegus",
    "Ласточка деревенская": "Hirundo rustica",
    "Лесной жаворонок": "Lullula arborea",
    "Малая поганка": "Tachybaptus ruficollis",
    "Мохноногий сыч": "Aegolius funereus",
    "Орел карлик": "Hieraaetus pennatus",
    "Орлан белохвост": "Haliaeetus albicilla",
    "Осоед": "Pernis apivorus",
    "Полевой лунь": "Circus cyaneus",
    "Рыжая цапля": "Ardea purpurea",
    "Свиристель": "Bombycilla garrulus",
    "Седой дятел": "Picus canus",
    "Серая утка": "Mareca strepera",
    "Снегирь": "Pyrrhula pyrrhula",
    "Средний пёстрый дятел": "Dendrocoptes medius",
    "Стриж черный": "Apus apus",
    "Трясогузка белая": "Motacilla alba",
    "Чернозобая гагара": "Gavia arctica",
    "Чёрный аист": "Ciconia nigra",
    "Байбак": "Marmota bobak",
    "Барсук": "Meles meles",
    "Благородный олень": "Cervus elaphus",
    "Бобр": "Castor fiber",
    "Выхухоль русская": "Desmana moschata",
    "Косуля": "Capreolus capreolus",
    "Крыса серая": "Rattus norvegicus",
    "Лесная соня": "Dryomys nitedula",
    "Малая вечерница": "Nyctalus leisleri",
    "Ночница брандта": "Myotis brandtii",
    "Обыкновенная белка": "Sciurus vulgaris",
    "Обыкновенная выдра": "Lutra lutra",
    "Ондатра": "Ondatra zibethicus",
    "Степная пеструшка": "Lagurus lagurus",
}

AUDIO_UPDATES = {
    "Большая синица": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/d/df/Parus_major.ogg",
        "audio_title": "Песня большой синицы",
        "audio_source": "Wikimedia Commons / Oona Raisanen",
        "audio_license": "Public domain",
    },
    "Серая неясыть": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/5/58/XN_Strix_aluco_003.ogg",
        "audio_title": "Крик серой неясыти",
        "audio_source": "Wikimedia Commons / Guido Gerding",
        "audio_license": "CC BY-SA 3.0 / GFDL",
    },
    "Озёрная лягушка": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/5/59/Marsh_frog_%28Pelophylax_ridibundus%29_call.ogg",
        "audio_title": "Брачный зов озёрной лягушки",
        "audio_source": "Wikimedia Commons / Llivermore",
        "audio_license": "CC BY-SA 4.0",
    },
    "Большая выпь": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/9/98/Botaurus_stellaris_-_Eurasian_Bittern_XC434683.mp3",
        "audio_title": "Голос большой выпи",
        "audio_source": "Wikimedia Commons / Joost van Bruggen",
        "audio_license": "CC BY-SA 4.0",
    },
    "Грач": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/c/cb/Rooks_in_rookery_and_nests_sounds.wav",
        "audio_title": "Голоса грачей в колонии",
        "audio_source": "Wikimedia Commons / Alwayswonder",
        "audio_license": "CC BY-SA 4.0",
    },
    "Домовый воробей": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/a/aa/Joseph_Sardin_-_Passer_domesticus_tschilp_call.oga",
        "audio_title": "Позывка домового воробья",
        "audio_source": "Wikimedia Commons / Joseph Sardin",
        "audio_license": "CC0",
    },
    "Клинтух": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/e/ee/Columba_oenas_-_Stock_Dove_XC489891.mp3",
        "audio_title": "Голос клинтуха",
        "audio_source": "Wikimedia Commons / Hannu Varkki",
        "audio_license": "CC BY-SA 4.0",
    },
    "Обыкновенная кукушка": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/d/dc/Cuculus_canorus_-_Common_Cuckoo_XC542432.mp3",
        "audio_title": "Кукование обыкновенной кукушки",
        "audio_source": "Wikimedia Commons / Benoît Van Hecke",
        "audio_license": "CC BY-SA 4.0",
    },
    "Обыкновенный скворец": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/c/ce/Sturnus_vulgaris_juveniles_sound_recording.ogg",
        "audio_title": "Голоса скворцов",
        "audio_source": "Wikimedia Commons / Kfrommolt",
        "audio_license": "CC BY-SA 3.0",
    },
    "Обыкновенный соловей": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/3/3a/Luscinia_luscinia_-_Thrush_Nightingale_XC537550.mp3",
        "audio_title": "Песня обыкновенного соловья",
        "audio_source": "Wikimedia Commons / Mats Havskogen",
        "audio_license": "CC BY-SA 4.0",
    },
    "Серая ворона": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/9/92/Corvus_cornix_-_Hooded_Crow_XC347296.mp3",
        "audio_title": "Крик серой вороны",
        "audio_source": "Wikimedia Commons / Kaveh Jamali",
        "audio_license": "CC BY-SA 4.0",
    },
    "Сизый голубь": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/1/1a/Columba_livia_-_Rock_Dove_XC539061.mp3",
        "audio_title": "Голос сизого голубя",
        "audio_source": "Wikimedia Commons / Marie-Lan Taÿ Pamart",
        "audio_license": "CC BY-SA 4.0",
    },
    "Сорока": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/b/b6/Pica_pica.ogg",
        "audio_title": "Крик сороки",
        "audio_source": "Wikimedia Commons / Oona Räisänen",
        "audio_license": "Public domain",
    },
    "Стриж черный": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/c/ce/Apus_apus_-_Common_Swift_XC554033.mp3",
        "audio_title": "Крик чёрного стрижа",
        "audio_source": "Wikimedia Commons / Luis Alvarez Menendez",
        "audio_license": "CC BY-SA 4.0",
    },
    "Чёрный стриж": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/c/ce/Apus_apus_-_Common_Swift_XC554033.mp3",
        "audio_title": "Крик чёрного стрижа",
        "audio_source": "Wikimedia Commons / Luis Alvarez Menendez",
        "audio_license": "CC BY-SA 4.0",
    },
    "Ёж обыкновенный": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/1/19/Braunigel_Drohger%C3%A4usche.ogg",
        "audio_title": "Защитные звуки ежа",
        "audio_source": "Wikimedia Commons / Richard Huber",
        "audio_license": "CC BY-SA 4.0",
    },
    "Беркут": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/c/cf/Golden_Eagle_%28Aquila_chrysaetos%29_%28W1CDR0001387_BD6%29.ogg",
        "audio_title": "Голос беркута",
        "audio_source": "Wikimedia Commons",
        "audio_license": "CC BY-SA 4.0",
    },
    "Белоспинный дятел": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/4/40/Feh%C3%A9rh%C3%A1t%C3%BA_fakop%C3%A1ncs_dob_-_Dendrocopos_leucotos.ogg",
        "audio_title": "Барабанная дробь белоспинного дятла",
        "audio_source": "Wikimedia Commons / Hangvadász",
        "audio_license": "CC BY-SA 3.0",
    },
    "Большая белая цапля": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/e/eb/Ardea_alba_-_Great_Egret_XC131650.ogg",
        "audio_title": "Голос большой белой цапли",
        "audio_source": "Wikimedia Commons / Jonathon Jongsma",
        "audio_license": "CC BY-SA 3.0",
    },
    "Большой веретенник": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/1/19/Limosa_limosa_-_Black-tailed_Godwit_XC129138.ogg",
        "audio_title": "Тревожная и полётная позывка большого веретенника",
        "audio_source": "Wikimedia Commons / Sudipto Roy",
        "audio_license": "CC BY-SA 3.0",
    },
    "Волчек (малая выпь)": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/8/82/Ixobrychus_minutus_-_Little_Bittern_XC480404.mp3",
        "audio_title": "Ночной полётный зов малой выпи",
        "audio_source": "Wikimedia Commons / Jens Loose",
        "audio_license": "CC BY-SA 4.0",
    },
    "Галка": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/8/8a/Coloeus_monedula_-_Western_Jackdaw_XC436939.mp3",
        "audio_title": "Крики галки",
        "audio_source": "Wikimedia Commons / Joost van Bruggen",
        "audio_license": "CC BY-SA 4.0",
    },
    "Горлица": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/6/64/Streptopelia_turtur_-_European_Turtle_Dove_XC582028.mp3",
        "audio_title": "Песня обыкновенной горлицы",
        "audio_source": "Wikimedia Commons / Benoît Van Hecke",
        "audio_license": "CC BY-SA 4.0",
    },
    "Длиннохвостая неясыть": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/d/d3/DM550173_Ural_owl_male_and_female_territorial_calls.ogg",
        "audio_title": "Территориальные крики длиннохвостой неясыти",
        "audio_source": "Wikimedia Commons / SanoAK: Alexander Kürthy",
        "audio_license": "CC BY-SA 4.0",
    },
    "Желна": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/2/22/Black_woodpecker_Dryocopus_martius%2C_flying_call.ogg",
        "audio_title": "Полётный крик желны",
        "audio_source": "Wikimedia Commons / SanoAK: Alexander Kürthy",
        "audio_license": "CC BY-SA 4.0",
    },
    "Змееяд": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/7/77/Circaetus_gallicus_-_Short-toed_Snake_Eagle_XC539306.mp3",
        "audio_title": "Голос змееяда",
        "audio_source": "Wikimedia Commons / Benoît Van Hecke",
        "audio_license": "CC BY-SA 4.0",
    },
    "Козодой": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/0/03/Caprimulgus_europaeus_-_European_Nightjar_XC432929.mp3",
        "audio_title": "Песня и крики козодоя",
        "audio_source": "Wikimedia Commons / Joost van Bruggen",
        "audio_license": "CC BY-SA 4.0",
    },
    "Кулик-сорока": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/8/86/Eurasian_Oystercatcher_%28Haematopus_ostralegus%29_%28W_HAEMATOPUS_OSTRALEGUS_R4_C7%29.ogg",
        "audio_title": "Крики кулика-сороки",
        "audio_source": "Wikimedia Commons",
        "audio_license": "CC BY 4.0",
    },
    "Ласточка деревенская": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/b/bc/Hirundo_rustica_-_Barn_Swallow_-_XC83449.ogg",
        "audio_title": "Песня деревенской ласточки",
        "audio_source": "Wikimedia Commons / Jonathon Jongsma",
        "audio_license": "CC BY-SA 3.0",
    },
    "Лесной жаворонок": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/d/da/Woodlark_%28Lullula_arborea%29_%28W1CDR0001500_BD8%29.ogg",
        "audio_title": "Песня лесного жаворонка",
        "audio_source": "Wikimedia Commons",
        "audio_license": "CC BY-SA 4.0",
    },
    "Малая поганка": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/0/0b/Tachybaptus_ruficollis_-_Little_Grebe_XC483193.mp3",
        "audio_title": "Ночной полётный зов малой поганки",
        "audio_source": "Wikimedia Commons / Jens Loose",
        "audio_license": "CC BY-SA 4.0",
    },
    "Мохноногий сыч": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/8/84/Aegolius_Funereus_Teritorial_call_-_song.ogg",
        "audio_title": "Территориальная песня мохноногого сыча",
        "audio_source": "Wikimedia Commons / SanoAK: Alexander Kürthy",
        "audio_license": "CC BY-SA 4.0",
    },
    "Орел карлик": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/b/bc/Booted_Eagle.ogg",
        "audio_title": "Голос орла-карлика",
        "audio_source": "Wikimedia Commons / Bubulcus",
        "audio_license": "CC BY 3.0",
    },
    "Осоед": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/8/8a/Pernis_apivorus_-_European_Honey_Buzzard_XC580934.mp3",
        "audio_title": "Полётная позывка осоеда",
        "audio_source": "Wikimedia Commons / Benoît Van Hecke",
        "audio_license": "CC BY-SA 4.0",
    },
    "Полевой лунь": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/9/9c/Circus_cyaneus_-_Hen_Harrier_XC558933.mp3",
        "audio_title": "Полётная позывка полевого луня",
        "audio_source": "Wikimedia Commons / Benoît Van Hecke",
        "audio_license": "CC BY-SA 4.0",
    },
    "Рыжая цапля": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/e/e8/Ardea_purpurea_-_Purple_Heron_XC135429.ogg",
        "audio_title": "Тревожный крик рыжей цапли",
        "audio_source": "Wikimedia Commons / Sudipto Roy",
        "audio_license": "CC BY-SA 3.0",
    },
    "Свиристель": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/4/46/Bombycilla_garrulus_-_Bohemian_Waxwing_XC132884.ogg",
        "audio_title": "Полётные позывки свиристеля",
        "audio_source": "Wikimedia Commons / Bushman",
        "audio_license": "CC BY-SA 3.0",
    },
    "Седой дятел": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/7/72/Picus_canus_-_Grey-headed_Woodpecker_XC310920.mp3",
        "audio_title": "Крик седого дятла",
        "audio_source": "Wikimedia Commons / Alexander Kürthy",
        "audio_license": "CC BY-SA 4.0",
    },
    "Серая утка": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/e/e2/Mareca_strepera_-_Gadwall_XC436359.mp3",
        "audio_title": "Полётные позывки серой утки",
        "audio_source": "Wikimedia Commons / Joost van Bruggen",
        "audio_license": "CC BY-SA 4.0",
    },
    "Снегирь": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/d/d2/Pyrrhula_pyrrhula_-_Eurasian_Bullfinch_XC543718.mp3",
        "audio_title": "Позывки снегиря",
        "audio_source": "Wikimedia Commons / Benoît Van Hecke",
        "audio_license": "CC BY-SA 4.0",
    },
    "Средний пёстрый дятел": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/9/97/Dendrocoptes_medius_-_Middle_Spotted_Woodpecker_XC612700.mp3",
        "audio_title": "Тревожный крик среднего пёстрого дятла",
        "audio_source": "Wikimedia Commons / Jesús Lavedán Rodríguez",
        "audio_license": "CC BY-SA 4.0",
    },
    "Сокол сапсан": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/c/ca/Halc%C3%B3n_peregrino.ogg",
        "audio_title": "Голос сапсана",
        "audio_source": "Wikimedia Commons / Sternanita3",
        "audio_license": "CC BY-SA 4.0",
    },
    "Трясогузка белая": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/4/42/Motacilla_alba_-_White_Wagtail_XC501786.mp3",
        "audio_title": "Позывка белой трясогузки",
        "audio_source": "Wikimedia Commons / Hannu Varkki",
        "audio_license": "CC BY-SA 4.0",
    },
    "Серая жаба": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Common_Toad_%28Bufo_bufo%29_%28W_BUFO_BUFO_R3_C2%29.ogg",
        "audio_title": "Брачные зовы серой жабы",
        "audio_source": "Wikimedia Commons",
        "audio_license": "CC BY 4.0",
    },
    "Травяная лягушка": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/7/72/Rana_temporaria_120329-015849.ogg",
        "audio_title": "Брачный хор травяной лягушки",
        "audio_source": "Wikimedia Commons / Gilles San Martin",
        "audio_license": "CC BY-SA 3.0",
    },
    "Чесночница": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/8/87/6_knoflookpad_individu_Pelobates_fuscus_individual.wav",
        "audio_title": "Зов чесночницы",
        "audio_source": "Wikimedia Commons / Baudewijn Odé",
        "audio_license": "CC BY-SA 4.0",
    },
    "Барсук": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/9/93/European_Badger_%28Meles_meles%29_%28W1CDR0001490_BD4%29.ogg",
        "audio_title": "Зов европейского барсука",
        "audio_source": "Wikimedia Commons",
        "audio_license": "CC BY-SA 4.0",
    },
    "Благородный олень": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/9/9b/Red_Deer_%28Cervus_elaphus%29_%28W1CDR0001424_BD3%29.ogg",
        "audio_title": "Рёв благородного оленя",
        "audio_source": "Wikimedia Commons",
        "audio_license": "CC BY-SA 4.0",
    },
    "Косуля": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/c/c8/Male_roe_deer_growl.ogg",
        "audio_title": "Рычание самца косули",
        "audio_source": "Wikimedia Commons / 1bumer",
        "audio_license": "CC BY-SA 4.0",
    },
    "Лисица обыкновенная": {
        "audio_url": "https://upload.wikimedia.org/wikipedia/commons/7/79/Red_Fox_%28Vulpes_vulpes%29_%28W1CDR0001529_BD12%29.ogg",
        "audio_title": "Лай обыкновенной лисицы",
        "audio_source": "Wikimedia Commons",
        "audio_license": "CC BY-SA 4.0",
    },
}

LOCAL_AUDIO_FILES = {
    "Большая синица": "parus-major.ogg",
    "Серая неясыть": "strix-aluco.ogg",
    "Озёрная лягушка": "pelophylax-ridibundus.ogg",
    "Большая выпь": "botaurus-stellaris.mp3",
    "Грач": "corvus-frugilegus.ogg",
    "Домовый воробей": "passer-domesticus.oga",
    "Клинтух": "columba-oenas.mp3",
    "Обыкновенная кукушка": "cuculus-canorus.mp3",
    "Обыкновенный скворец": "sturnus-vulgaris.ogg",
    "Обыкновенный соловей": "luscinia-luscinia.mp3",
    "Серая ворона": "corvus-cornix.mp3",
    "Сизый голубь": "columba-livia.mp3",
    "Сорока": "pica-pica.ogg",
    "Стриж черный": "apus-apus.mp3",
    "Чёрный стриж": "apus-apus.mp3",
    "Ёж обыкновенный": "erinaceus-europaeus.ogg",
    "Беркут": "aquila-chrysaetos.ogg",
    "Белоспинный дятел": "dendrocopos-leucotos.ogg",
    "Большая белая цапля": "ardea-alba.ogg",
    "Большой веретенник": "limosa-limosa.ogg",
    "Волчек (малая выпь)": "ixobrychus-minutus.mp3",
    "Галка": "coloeus-monedula.mp3",
    "Горлица": "streptopelia-turtur.mp3",
    "Длиннохвостая неясыть": "strix-uralensis.ogg",
    "Желна": "dryocopus-martius.ogg",
    "Змееяд": "circaetus-gallicus.mp3",
    "Козодой": "caprimulgus-europaeus.mp3",
    "Кулик-сорока": "haematopus-ostralegus.ogg",
    "Ласточка деревенская": "hirundo-rustica.ogg",
    "Лесной жаворонок": "lullula-arborea.ogg",
    "Малая поганка": "tachybaptus-ruficollis.mp3",
    "Мохноногий сыч": "aegolius-funereus.ogg",
    "Орел карлик": "hieraaetus-pennatus.ogg",
    "Осоед": "pernis-apivorus.mp3",
    "Полевой лунь": "circus-cyaneus.mp3",
    "Рыжая цапля": "ardea-purpurea.ogg",
    "Свиристель": "bombycilla-garrulus.ogg",
    "Седой дятел": "picus-canus.mp3",
    "Серая утка": "mareca-strepera.mp3",
    "Снегирь": "pyrrhula-pyrrhula.mp3",
    "Средний пёстрый дятел": "dendrocoptes-medius.mp3",
    "Сокол сапсан": "falco-peregrinus.ogg",
    "Трясогузка белая": "motacilla-alba.mp3",
    "Серая жаба": "bufo-bufo.ogg",
    "Травяная лягушка": "rana-temporaria.ogg",
    "Чесночница": "pelobates-fuscus.mp3",
    "Барсук": "meles-meles.ogg",
    "Благородный олень": "cervus-elaphus.ogg",
    "Косуля": "capreolus-capreolus.ogg",
    "Лисица обыкновенная": "vulpes-vulpes.ogg",
}

XENO_AUDIO_SOURCE_OVERRIDES = {
    "Ёж обыкновенный": ("1017411", "David Tattersley", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
    "Беркут": ("1045328", "Lars Edenius", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
    "Белоспинный дятел": ("1102707", "Lars Edenius", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
    "Длиннохвостая неясыть": ("1097186", "Jens Schöller", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
    "Желна": ("988771", "FRIEDRICH Richard", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
    "Кулик-сорока": ("1101393", "Astrid Cervantes", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
    "Лесной жаворонок": ("1100453", "Teus Luijendijk", "Creative Commons Attribution-NonCommercial-NoDerivs 4.0"),
    "Мохноногий сыч": ("1097665", "Dag Österlund", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
    "Орел карлик": ("1067347", "Albert Lastukhin", "Creative Commons Attribution-NonCommercial-NoDerivs 4.0"),
    "Сокол сапсан": ("1092708", "Romuald Mikusek", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
    "Серая жаба": ("938900", "Dimitri", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
    "Травяная лягушка": ("893542", "Simon Elliott", "Creative Commons Attribution-NonCommercial-NoDerivs 4.0"),
    "Чесночница": ("949827", "Olivier SWIFT, Ludivine DELAMARE", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
    "Барсук": ("960960", "Lars Edenius", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
    "Благородный олень": ("1046509", "David Bissett", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
    "Косуля": ("1100395", "Cedric Mroczko", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
    "Лисица обыкновенная": ("1100142", "Thijs Calu", "Creative Commons Attribution-NonCommercial-ShareAlike 4.0"),
}

for name_ru, filename in LOCAL_AUDIO_FILES.items():
    AUDIO_UPDATES[name_ru]["audio_url"] = f"/api/media/species-audio/{filename}"

for name_ru, (xc_id, recordist, license_name) in XENO_AUDIO_SOURCE_OVERRIDES.items():
    AUDIO_UPDATES[name_ru]["audio_source"] = f"Xeno-canto XC{xc_id} / {recordist}"
    AUDIO_UPDATES[name_ru]["audio_license"] = license_name


def _species_by_name(db: Session, name_ru: str) -> Species | None:
    return (
        db.query(Species)
        .filter(func.lower(Species.name_ru) == name_ru.lower())
        .first()
    )


def _count_species_references(db: Session, species: Species) -> int:
    observations = (
        db.query(func.count(Observation.id))
        .filter(Observation.species_id == species.id)
        .scalar()
        or 0
    )
    discoveries = (
        db.query(func.count(SpeciesFirstDiscovery.id))
        .filter(SpeciesFirstDiscovery.species_id == species.id)
        .scalar()
        or 0
    )
    return observations + discoveries


def _species_payload(item: dict[str, Any], *, for_create: bool) -> dict[str, Any]:
    values: dict[str, Any] = {
        "name_ru": item["name_ru"],
        "name_latin": item["name_latin"],
        "group": SpeciesGroup(item["group"]),
        "category": SpeciesCategory(item["category"]),
    }

    defaults = {
        "conservation_status": None,
        "is_poisonous": False,
        "season_info": None,
        "biotopes": None,
        "description": None,
        "do_dont_rules": None,
        "qr_url": None,
        "photo_urls": None,
    }
    for field, default in defaults.items():
        if field in item:
            values[field] = item[field]
        elif for_create:
            values[field] = default

    return values


def _assign_if_changed(species: Species, values: dict[str, Any]) -> bool:
    changed = False
    for field, value in values.items():
        if getattr(species, field) != value:
            setattr(species, field, value)
            changed = True
    return changed


def _merge_duplicate_species(
    db: Session,
    canonical: Species,
    duplicate: Species,
    summary: dict[str, Any],
) -> None:
    if canonical.id == duplicate.id:
        return

    db.query(Observation).filter(Observation.species_id == duplicate.id).update(
        {Observation.species_id: canonical.id},
        synchronize_session=False,
    )

    duplicate_discovery = (
        db.query(SpeciesFirstDiscovery)
        .filter(SpeciesFirstDiscovery.species_id == duplicate.id)
        .first()
    )
    if duplicate_discovery:
        canonical_discovery = (
            db.query(SpeciesFirstDiscovery)
            .filter(SpeciesFirstDiscovery.species_id == canonical.id)
            .first()
        )
        if canonical_discovery:
            db.delete(duplicate_discovery)
        else:
            duplicate_discovery.species_id = canonical.id

    db.delete(duplicate)
    summary["merged"] += 1


def _delete_if_unreferenced(db: Session, species: Species, summary: dict[str, Any]) -> None:
    if _count_species_references(db, species) > 0:
        summary["skipped"].append(species.name_ru)
        return

    db.delete(species)
    summary["deleted"] += 1


def _upsert_species(db: Session, item: dict[str, Any], summary: dict[str, Any]) -> Species:
    aliases = item.get("aliases", [])
    species = _species_by_name(db, item["name_ru"])
    if species is None:
        for alias in aliases:
            species = _species_by_name(db, alias)
            if species is not None:
                break

    values = _species_payload(item, for_create=species is None)
    if species is None:
        species = Species(**values)
        db.add(species)
        db.flush()
        summary["created"] += 1
    elif _assign_if_changed(species, values):
        summary["updated"] += 1

    for alias in aliases:
        duplicate = _species_by_name(db, alias)
        if duplicate is not None and duplicate.id != species.id:
            _merge_duplicate_species(db, species, duplicate, summary)

    return species


def _merge_known_duplicates(db: Session, summary: dict[str, Any]) -> None:
    for canonical_name, duplicate_name in CANONICAL_DUPLICATES:
        canonical = _species_by_name(db, canonical_name)
        duplicate = _species_by_name(db, duplicate_name)

        if canonical and duplicate:
            _merge_duplicate_species(db, canonical, duplicate, summary)
        elif duplicate and not canonical:
            duplicate.name_ru = canonical_name
            summary["updated"] += 1


def _normalize_empty_photo_arrays(db: Session, summary: dict[str, Any]) -> None:
    rows = (
        db.query(Species)
        .filter(
            Species.photo_urls.is_not(None),
            func.coalesce(func.array_length(Species.photo_urls, 1), 0) == 0,
        )
        .all()
    )
    for species in rows:
        species.photo_urls = None
        summary["updated"] += 1


def _apply_audio_updates(db: Session, summary: dict[str, Any]) -> None:
    for name_ru, values in AUDIO_UPDATES.items():
        species = _species_by_name(db, name_ru)
        if species is not None and _assign_if_changed(species, values):
            summary["updated"] += 1


def _apply_photo_updates(db: Session, summary: dict[str, Any]) -> None:
    for name_ru, photo_urls in PHOTO_UPDATES.items():
        species = _species_by_name(db, name_ru)
        if species is not None and not species.photo_urls:
            species.photo_urls = photo_urls
            summary["updated"] += 1


def _apply_latin_name_updates(db: Session, summary: dict[str, Any]) -> None:
    for name_ru, name_latin in LATIN_NAME_UPDATES.items():
        species = _species_by_name(db, name_ru)
        if species is not None and _assign_if_changed(
            species,
            {"name_latin": name_latin},
        ):
            summary["updated"] += 1


def apply_content_review(db: Session) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "created": 0,
        "updated": 0,
        "deleted": 0,
        "merged": 0,
        "skipped": [],
    }

    for item in CATALOG_UPSERTS:
        _upsert_species(db, item, summary)

    _merge_known_duplicates(db, summary)

    for name_ru, photo_urls in PHOTO_OVERRIDES.items():
        species = _species_by_name(db, name_ru)
        if species is not None and species.photo_urls != photo_urls:
            species.photo_urls = photo_urls
            summary["updated"] += 1

    _normalize_empty_photo_arrays(db, summary)
    _apply_latin_name_updates(db, summary)
    _apply_photo_updates(db, summary)
    _apply_audio_updates(db, summary)

    for name_ru in REMOVED_SPECIES_NAMES:
        species = _species_by_name(db, name_ru)
        if species is not None:
            _delete_if_unreferenced(db, species, summary)

    db.flush()
    return summary


def main() -> None:
    db = SessionLocal()
    try:
        summary = apply_content_review(db)
        db.commit()
        print(f"Applied content review 2026-04-17: {summary}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
