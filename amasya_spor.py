#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Amasya Spor Radar v4.0 - API'LI GERCEK ZAMANLI VERI
NewsAPI + Reddit API ile canli haber ve tartisma takibi.
"""

import streamlit as st
import requests
from bs4 import BeautifulSoup
import feedparser
import json
import os
import re
import datetime
import time
import random
from dateutil import parser as date_parser
from urllib.parse import urljoin, quote
import pandas as pd
from collections import defaultdict
import html
import base64
import io

# =============================================================================
# SABITLER
# =============================================================================
CONFIG_DOSYA = "config.json"
CACHE_DOSYA = "cache.json"
VERSIYON = "4.0"

NEWSAPI_BASE = "https://newsapi.org/v2/everything"
REDDIT_BASE = "https://www.reddit.com/search.json"

SPOR_KELIMELERI = [
    "spor", "futbol", "voleybol", "basketbol", "gures", "hentbol", "atletizm",
    "yuzme", "okculuk", "judo", "taekwondo", "tenis", "boks", "karate",
    "amasyaspor", "yesil simsekler", "sehzadeler", "taraftar", "mac",
    "musabaka", "turnuva", "sampiyona", "lig", "kupa", "federasyon",
    "tff", "tvf", "tbf", "tgf", "gsb", "genclik ve spor", "belediyespor",
    "stadyum", "spor salonu", "stad", "saha", "antrenor", "teknik direktor",
    "transfer", "gol", "sampiyon", "basari", "madalya", "kazan", "maglubiyet",
    "galibiyet", "hakem", "takim", "oyuncu", "sporcu", "mili takim", "altyapi"
]

ETKINLIK_SPOR_KELIMELERI = [
    "mac", "musabaka", "turnuva", "sampiyona", "lig", "kupa", "futbol",
    "voleybol", "basketbol", "gures", "yarisma", "etkinlik", "spor",
    "karsilasma", "derbi", "spor salonu", "stadyum", "stad", "saha",
    "antrenman", "kamp", "davet", "acilis", "toren", "odul", "madalya"
]

DEFAULT_CONFIG = {
    "uygulama_adi": "Amasya Spor Radar",
    "versiyon": "4.0",
    "aciklama": "Amasya'daki tum sportif faaliyetleri - API'LI GERCEK ZAMANLI VERI",
    "api_anahtarlari": {
        "newsapi": "",
        "reddit_client_id": "",
        "reddit_client_secret": "",
        "reddit_user_agent": "AmasyaSporRadar/4.0"
    },
    "kaynaklar": {
        "rss_kaynaklari": [
            {"ad": "Google News - Amasya Spor", "tur": "google_news", "sorgu": "Amasya+spor", "aktif": True, "kategori": "genel_haber"},
            {"ad": "Google News - Amasyaspor FK", "tur": "google_news", "sorgu": "Amasyaspor", "aktif": True, "kategori": "spor_haber"},
            {"ad": "Google News - Amasya Futbol", "tur": "google_news", "sorgu": "Amasya+futbol", "aktif": True, "kategori": "spor_haber"},
            {"ad": "Google News - Amasya Voleybol", "tur": "google_news", "sorgu": "Amasya+voleybol", "aktif": True, "kategori": "spor_haber"},
            {"ad": "Google News - Amasya Gures", "tur": "google_news", "sorgu": "Amasya+gures", "aktif": True, "kategori": "spor_haber"},
            {"ad": "Google News - Yesil Simsekler", "tur": "google_news", "sorgu": "Yeşil+Şimşekler+Amasya", "aktif": True, "kategori": "taraftar"},
            {"ad": "Google News - Sehzadeler", "tur": "google_news", "sorgu": "Şehzadeler+Amasya+taraftar", "aktif": True, "kategori": "taraftar"},
            {"ad": "Google News - Amasya Protokol Spor", "tur": "google_news", "sorgu": "Amasya+vali+spor+protokol", "aktif": True, "kategori": "resmi"},
            {"ad": "Google News - Amasya Belediye Spor", "tur": "google_news", "sorgu": "Amasya+belediye+spor", "aktif": True, "kategori": "belediye"},
            {"ad": "Google News - Amasya Universite Spor", "tur": "google_news", "sorgu": "Amasya+universite+spor", "aktif": True, "kategori": "universite"},
            {"ad": "TRT Spor RSS", "url": "https://www.trtspor.com.tr/rss/spor.rss", "tur": "rss", "aktif": True, "kategori": "spor_haber"},
            {"ad": "NTV Spor RSS", "url": "https://www.ntvspor.net/rss/spor.rss", "tur": "rss", "aktif": True, "kategori": "spor_haber"},
            {"ad": "Sporx RSS", "url": "https://www.sporx.com/rss", "tur": "rss", "aktif": True, "kategori": "spor_haber"},
            {"ad": "Milliyet RSS", "url": "https://www.milliyet.com.tr/rss/rssNew/SonDakikaRss.xml", "tur": "rss", "aktif": True, "kategori": "genel_haber"},
            {"ad": "Hurriyet RSS", "url": "https://www.hurriyet.com.tr/rss/gundem", "tur": "rss", "aktif": True, "kategori": "genel_haber"},
        ],
        "api_kaynaklari": [
            {"ad": "NewsAPI - Amasya Spor", "tur": "newsapi", "sorgu": "Amasya AND spor", "aktif": True, "kategori": "api_haber"},
            {"ad": "NewsAPI - Amasyaspor", "tur": "newsapi", "sorgu": "Amasyaspor", "aktif": True, "kategori": "api_haber"},
            {"ad": "NewsAPI - Amasya Taraftar", "tur": "newsapi", "sorgu": "Amasya AND (taraftar OR futbol OR voleybol)", "aktif": True, "kategori": "api_haber"},
            {"ad": "Reddit - Amasya Spor", "tur": "reddit", "sorgu": "Amasya spor", "aktif": True, "kategori": "reddit"},
            {"ad": "Reddit - Turkish Football", "tur": "reddit", "sorgu": "Turkish football Amasya", "aktif": True, "kategori": "reddit"},
        ],
        "web_siteleri": [
            {"ad": "TFF - Amasya Il Temsilciligi", "url": "https://www.tff.org/Default.aspx?pageID=527&ilID=5", "tur": "web", "aktif": False, "kategori": "federasyon", "secici": ".news-item, .haber-item"},
            {"ad": "Genclik ve Spor Il Mudurlugu", "url": "https://amasya.gsb.gov.tr/", "tur": "web", "aktif": False, "kategori": "resmi", "secici": ".news-item, .announcement"},
            {"ad": "Amasya Belediyesi - Spor", "url": "https://www.amasya.bel.tr/haberler/spor", "tur": "web", "aktif": False, "kategori": "belediye", "secici": ".news-item, .post, .haber"},
            {"ad": "Amasya Valiligi", "url": "https://www.amasya.gov.tr/", "tur": "web", "aktif": False, "kategori": "resmi", "secici": ".announcement, .duyuru"},
            {"ad": "TVF", "url": "https://www.tvf.org.tr/", "tur": "web", "aktif": False, "kategori": "federasyon", "secici": ".news-item, .haber"},
            {"ad": "Amasyaspor FK", "url": "https://www.amasyasporfk.com/", "tur": "web", "aktif": False, "kategori": "kulup", "secici": ".news-item, .post, .haber"},
        ],
        "sosyal_medya": [
            {"ad": "Yesil Simsekler (Nitter)", "kullanici": "yesilsimsekler", "tur": "nitter", "platform": "twitter", "aktif": True, "kategori": "taraftar", "grup": "Yesil Simsekler"},
            {"ad": "Sehzadeler (Nitter)", "kullanici": "sehzadeler", "tur": "nitter", "platform": "twitter", "aktif": True, "kategori": "taraftar", "grup": "Sehzadeler"},
            {"ad": "Amasyaspor FK (Nitter)", "kullanici": "amasyasporfk", "tur": "nitter", "platform": "twitter", "aktif": True, "kategori": "kulup", "grup": "Amasyaspor FK"},
        ],
        "etkinlik_kaynaklari": [
            {"ad": "TFF Musabaka Takvimi", "url": "https://www.tff.org/Default.aspx?pageID=1428", "tur": "web", "aktif": False, "kategori": "musabaka"},
            {"ad": "TVF Musabaka Takvimi", "url": "https://www.tvf.org.tr/fikstur/", "tur": "web", "aktif": False, "kategori": "musabaka"},
        ]
    },
    "taraftar_gruplari": [
        {"ad": "Yesil Simsekler", "kisa_ad": "yesilsimsekler", "renkler": ["Yesil", "Siyah"], "takim": "Amasyaspor FK", "platformlar": {"twitter": "yesilsimsekler", "instagram": "yesilsimsekler", "facebook": "yesilsimsekler"}, "aktif": True, "oncelik": 1},
        {"ad": "Sehzadeler", "kisa_ad": "sehzadeler", "renkler": ["Yesil", "Beyaz"], "takim": "Amasyaspor FK", "platformlar": {"twitter": "sehzadeler", "instagram": "sehzadeler", "facebook": "sehzadeler"}, "aktif": True, "oncelik": 1},
        {"ad": "Amasyaspor Taraftarlari", "kisa_ad": "amasyaspor_taraftar", "renkler": ["Yesil", "Siyah"], "takim": "Amasyaspor FK", "platformlar": {"twitter": "amasyaspor_taraftar", "instagram": "amasyaspor_taraftar"}, "aktif": True, "oncelik": 2},
        {"ad": "Amasya Genclik", "kisa_ad": "amasya_genclik", "renkler": ["Kirmizi", "Beyaz"], "takim": "Cesitli", "platformlar": {"twitter": "amasya_genclik", "instagram": "amasya_genclik"}, "aktif": True, "oncelik": 2}
    ],
    "spor_branslari": [
        {"ad": "Futbol", "kisa_ad": "futbol", "takimlar": ["Amasyaspor FK", "Amasya Belediyespor", "Merzifonspor"], "federasyon": "TFF", "oncelik": 1, "amasya_basarilari": "Amasyaspor FK tarihsel basarilari"},
        {"ad": "Voleybol", "kisa_ad": "voleybol", "takimlar": ["Amasya Belediyespor Voleybol", "Amasya Universitesi Voleybol"], "federasyon": "TVF", "oncelik": 1, "amasya_basarilari": "Kadin voleybol takimlari bolgesel basarilar"},
        {"ad": "Basketbol", "kisa_ad": "basketbol", "takimlar": ["Amasya Basketbol"], "federasyon": "TBF", "oncelik": 2, "amasya_basarilari": "Genclik kategorilerinde basarilar"},
        {"ad": "Gures", "kisa_ad": "gures", "takimlar": ["Amasya Gures Takimi"], "federasyon": "TGF", "oncelik": 1, "amasya_basarilari": "Geleneksel yagli guresler"},
        {"ad": "Okculuk", "kisa_ad": "okculuk", "takimlar": ["Amasya Okculuk"], "federasyon": "TOKF", "oncelik": 2, "amasya_basarilari": "Genclik ve spor mudurlugu altyapi basarilari"},
        {"ad": "Atletizm", "kisa_ad": "atletizm", "takimlar": ["Amasya Atletizm"], "federasyon": "TAF", "oncelik": 2, "amasya_basarilari": "Bolgesel yarisamalarda madalyalar"},
        {"ad": "Yuzme", "kisa_ad": "yuzme", "takimlar": ["Amasya Yuzme"], "federasyon": "TYF", "oncelik": 2, "amasya_basarilari": "Genclik kategorilerinde basarilar"},
        {"ad": "Judo", "kisa_ad": "judo", "takimlar": ["Amasya Judo"], "federasyon": "TJF", "oncelik": 2, "amasya_basarilari": "Okul sporlari basarilari"},
        {"ad": "Taekwondo", "kisa_ad": "taekwondo", "takimlar": ["Amasya Taekwondo"], "federasyon": "TTF", "oncelik": 2, "amasya_basarilari": "Genclik kategorilerinde madalyalar"},
        {"ad": "Hentbol", "kisa_ad": "hentbol", "takimlar": ["Amasya Hentbol"], "federasyon": "THF", "oncelik": 2, "amasya_basarilari": "Kadin hentbol takimi bolgesel basarilar"}
    ],
    "etiketler": ["#AmasyaSpor", "#Amasyaspor", "#AmasyaSporFK", "#YesilSimsekler", "#Sehzadeler", "#AmasyaFutbol", "#AmasyaVoleybol", "#AmasyaGures", "#AmasyaBasketbol", "#AmasyaGenclik", "#AmasyaGSB", "#AmasyaBelediyespor", "#AmasyaEtkinlik", "#AmasyaMusabaka", "#AmasyaTaraftar", "#YesilBeyaz"],
    "anahtar_kelimeler": ["Amasya spor", "Amasyaspor", "Amasya futbol", "Amasya voleybol", "Amasya gures", "Amasya basketbol", "Amasya hentbol", "Amasya atletizm", "Amasya yuzme", "Amasya okculuk", "Amasya judo", "Amasya taekwondo", "Yesil Simsekler", "Sehzadeler", "Amasya taraftar", "Amasya musabaka", "Amasya turnuva", "Amasya sampiyona", "Amasya lig", "Amasya kupa", "Amasya belediyespor", "Amasya genclik spor", "Amasya il mudurlugu spor", "Amasya protokol spor", "Amasya vali spor", "Amasya belediye baskani spor", "Amasya milletvekili spor", "Amasya spor yatirim", "Amasya spor tesis", "Amasya stad", "Amasya 12 Haziran Stadyumu", "Amasya spor salonu", "Amasya yuzme havuzu", "Amasya spor kompleksi"],
    "ayarlar": {
        "ai_modul_aktif": False,
        "ai_modul_adi": "ozetleyici",
        "otomatik_tarama_aktif": False,
        "otomatik_tarama_araligi_saat": 6,
        "bildirim_aktif": False,
        "bildirim_kanali": "yok",
        "veri_saklama_gun": 30,
        "sayfa_basina_kayit": 20,
        "zaman_dilimi": "Europe/Istanbul",
        "dil": "tr",
        "arama_gun_araligi": 7,
        "kaynak_zaman_asimi_saniye": 15,
        "max_icerik_uzunluk": 5000,
        "min_icerik_uzunluk": 50,
        "gorunum_tema": "acik",
        "varsayilan_siralama": "tarih_yeni",
        "varsayilan_filtre": "tum",
        "protokol_vurgula": True,
        "taraftar_vurgula": True,
        "etkinlik_karti_goster": True,
        "kaynak_rozetleri_goster": True,
        "duygu_rozetleri_goster": True,
        "brans_rozetleri_goster": True,
        "grup_rozetleri_goster": True,
        "tarih_formati": "dd.mm.yyyy HH:MM",
        "sidebar_acik": True,
        "sayfa_basligi": "Amasya Spor Radar",
        "favicon": "futbol",
        "ozellestirilmis_css": "",
        "disa_aktar_format": "excel",
        "disa_aktar_dil": "tr",
        "bildirim_ses": False,
        "bildirim_masaustu": False,
        "gizli_kaynaklari_goster": False,
        "debug_modu": False,
        "spor_filtre_skor_esigi": 1,
        "sadece_spor_icerik": True,
        "etkinlik_sadece_spor": True,
        "cache_bypass": False,
        "protokol_kelime_listesi": "vali,belediye baskani,milletvekili,kaymakam,protokol,genclik ve spor il muduru,gsb muduru,rektor,dekan,spor il muduru,bakan,baskan,mudur",
        "yer_kelime_listesi": "amasya,12 haziran stadyumu,spor salonu,spor kompleksi,yuzme havuzu,stad,salon,merzifon,suluova,tasova,gumushacikoy",
        "olumlu_duygu_kelimeleri": "basari,zafer,sampiyon,kazandi,guzel,harika,tebrik,bravo,muhtesem,gurur,mutlu,sevinc",
        "olumsuz_duygu_kelimeleri": "maglup,kaybetti,basarisiz,kotu,berbat,protesto,eylem,kavga,sikayet,sorun,husran,uzucu"
    },
    "ai_modulleri": {
        "ozetleyici": {"aktif": False, "aciklama": "Haberleri otomatik ozetler", "tip": "yerel", "parametreler": {"max_cumle": 3, "min_cumle": 1}},
        "duygu_analizi": {"aktif": False, "aciklama": "Taraftar paylasimlarinin duygu durumunu analiz eder", "tip": "yerel", "parametreler": {}},
        "etkinlik_tanima": {"aktif": False, "aciklama": "Metin icinden etkinlik bilgilerini cikarir", "tip": "yerel", "parametreler": {}}
    }
}

# =============================================================================
# YARDIMCI FONKSIYONLAR
# =============================================================================

def config_oku():
    try:
        with open(CONFIG_DOSYA, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        try:
            with open(CONFIG_DOSYA, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
            return DEFAULT_CONFIG.copy()
        except:
            return DEFAULT_CONFIG.copy()

def config_yaz(cfg):
    try:
        with open(CONFIG_DOSYA, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Config kaydetme hatasi: {e}")
        return False

def config_indir(cfg):
    json_str = json.dumps(cfg, ensure_ascii=False, indent=2)
    b64 = base64.b64encode(json_str.encode()).decode()
    return f'<a href="data:file/json;base64,{b64}" download="config.json">Config.json Indir</a>'

def config_yukle(uploaded_file):
    try:
        content = uploaded_file.read().decode('utf-8')
        new_cfg = json.loads(content)
        with open(CONFIG_DOSYA, 'w', encoding='utf-8') as f:
            json.dump(new_cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Config yukleme hatasi: {e}")
        return False

def cache_oku():
    if os.path.exists(CACHE_DOSYA):
        try:
            with open(CACHE_DOSYA, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"veriler": [], "son_tarama": None, "istatistikler": {}}
    return {"veriler": [], "son_tarama": None, "istatistikler": {}}

def cache_yaz(veri):
    try:
        with open(CACHE_DOSYA, 'w', encoding='utf-8') as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Cache yazma hatasi: {e}")

def metin_temizle(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def tarih_parse(tarih_str):
    if not tarih_str:
        return datetime.datetime.now()
    try:
        return date_parser.parse(str(tarih_str))
    except:
        pass
    aylar = {'ocak': 1, 'subat': 2, 'mart': 3, 'nisan': 4, 'mayis': 5, 'haziran': 6, 'temmuz': 7, 'agustos': 8, 'eylul': 9, 'ekim': 10, 'kasim': 11, 'aralik': 12}
    pattern = r'(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})'
    match = re.search(pattern, str(tarih_str).lower())
    if match:
        gun, ay_str, yil = match.groups()
        ay = aylar.get(ay_str, 1)
        return datetime.datetime(int(yil), ay, int(gun))
    pattern = r'(\d{1,2})[./](\d{1,2})[./](\d{4})'
    match = re.search(pattern, str(tarih_str))
    if match:
        gun, ay, yil = map(int, match.groups())
        return datetime.datetime(yil, ay, gun)
    return datetime.datetime.now()

def kisa_tarih(dt):
    if isinstance(dt, str):
        dt = tarih_parse(dt)
    return dt.strftime("%d.%m.%Y %H:%M")

def zaman_farki(dt):
    if isinstance(dt, str):
        dt = tarih_parse(dt)
    simdi = datetime.datetime.now(dt.tzinfo) if dt.tzinfo else datetime.datetime.now()
    fark = simdi - dt
    if fark.days > 0:
        return f"{fark.days} gun once"
    saat = fark.seconds // 3600
    if saat > 0:
        return f"{saat} saat once"
    dakika = fark.seconds // 60
    if dakika > 0:
        return f"{dakika} dakika once"
    return "Az once"

def basit_ozetle(metin, cumle_sayisi=3):
    if not metin:
        return ""
    cumleler = re.split(r'(?<=[.!?])\s+', metin)
    cumleler = [c for c in cumleler if len(c.strip()) > 10]
    if len(cumleler) <= cumle_sayisi:
        return metin
    return " ".join(cumleler[:cumle_sayisi]) + "..."

def spor_skor_hesapla(metin, spor_kelimeleri):
    if not metin:
        return 0
    metin_lower = metin.lower()
    skor = 0
    for kelime in spor_kelimeleri:
        if kelime in metin_lower:
            skor += 1
    return skor

def etkinlik_bilgisi_cikar(metin, cfg_ayarlar):
    bilgi = {"tarih": None, "yer": None, "katilimci": None, "protokol": False, "spor_etkinlik": False}
    if not metin:
        return bilgi
    metin_lower = metin.lower()
    spor_skor = spor_skor_hesapla(metin, ETKINLIK_SPOR_KELIMELERI)
    esik = int(cfg_ayarlar.get("spor_filtre_skor_esigi", 1))
    if spor_skor < esik and cfg_ayarlar.get("etkinlik_sadece_spor", True):
        return bilgi
    bilgi["spor_etkinlik"] = True
    tarih_patternler = [
        r'(\d{1,2})\s+(ocak|subat|mart|nisan|mayis|haziran|temmuz|agustos|eylul|ekim|kasim|aralik)\s+(\d{4})',
        r'(\d{1,2})[./](\d{1,2})[./](\d{4})',
        r'(\d{1,2})[./](\d{1,2})[./](\d{2})',
    ]
    for pattern in tarih_patternler:
        match = re.search(pattern, metin_lower)
        if match:
            bilgi["tarih"] = match.group(0)
            break
    yer_listesi = cfg_ayarlar.get("yer_kelime_listesi", "amasya,stadyum").split(",")
    for yer in yer_listesi:
        yer = yer.strip().lower()
        if yer and yer in metin_lower:
            bilgi["yer"] = yer.title() if yer != "amasya" else "Amasya"
            break
    protokol_listesi = cfg_ayarlar.get("protokol_kelime_listesi", "vali,belediye baskani").split(",")
    katilimcilar = []
    for kelime in protokol_listesi:
        kelime = kelime.strip().lower()
        if kelime and kelime in metin_lower:
            katilimcilar.append(kelime.title())
            bilgi["protokol"] = True
    if katilimcilar:
        bilgi["katilimci"] = ", ".join(katilimcilar[:3])
    return bilgi

def spor_bransi_tespit(metin, branslar):
    bulunan = []
    if not metin:
        return bulunan
    metin_lower = metin.lower()
    for brans in branslar:
        if brans["kisa_ad"] in metin_lower or brans["ad"].lower() in metin_lower:
            bulunan.append(brans)
    return bulunan

def taraftar_grubu_tespit(metin, gruplar):
    bulunan = []
    if not metin:
        return bulunan
    metin_lower = metin.lower()
    for grup in gruplar:
        if grup["kisa_ad"] in metin_lower or grup["ad"].lower() in metin_lower:
            bulunan.append(grup)
    return bulunan

def duygu_analizi_basit(metin, cfg_ayarlar):
    if not metin:
        return "notr"
    metin_lower = metin.lower()
    olumlu = [k.strip() for k in cfg_ayarlar.get("olumlu_duygu_kelimeleri", "basari,zafer").split(",") if k.strip()]
    olumsuz = [k.strip() for k in cfg_ayarlar.get("olumsuz_duygu_kelimeleri", "maglup,kaybetti").split(",") if k.strip()]
    olumlu_say = sum(1 for k in olumlu if k in metin_lower)
    olumsuz_say = sum(1 for k in olumsuz if k in metin_lower)
    if olumlu_say > olumsuz_say:
        return "olumlu"
    elif olumsuz_say > olumlu_say:
        return "olumsuz"
    return "notr"

# =============================================================================
# HTTP ISTEK YONETIMI
# =============================================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

def get_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

def http_get(url, timeout=15, retries=2):
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, headers=get_headers(), timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'
            return response
        except requests.exceptions.Timeout:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise
        except requests.exceptions.RequestException:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise
    return None

# =============================================================================
# API VERI TOPLAMA MOTORU - GERCEK ZAMANLI
# =============================================================================

def newsapi_cek(kaynak, cfg, cfg_ayarlar, limit=20):
    """NewsAPI'den gercek zamanli haber ceker. API key gerekli."""
    veriler = []
    api_key = cfg.get("api_anahtarlari", {}).get("newsapi", "")
    if not api_key:
        return veriler

    try:
        sorgu = kaynak.get("sorgu", "Amasya spor")
        url = f"{NEWSAPI_BASE}?q={quote(sorgu)}&language=tr&sortBy=publishedAt&pageSize={limit}&apiKey={api_key}"

        response = requests.get(url, timeout=15)
        data = response.json()

        if data.get("status") != "ok":
            if cfg_ayarlar.get("debug_modu", False):
                st.warning(f"NewsAPI hata: {data.get('message', 'Bilinmiyor')}")
            return veriler

        for article in data.get("articles", []):
            baslik = metin_temizle(article.get("title", ""))
            ozet = metin_temizle(article.get("description", ""))
            link = article.get("url", "")
            tarih_str = article.get("publishedAt", "")
            kaynak_ad = article.get("source", {}).get("name", "NewsAPI")

            if not baslik:
                continue

            tarih = tarih_parse(tarih_str)
            icerik = f"{baslik}. {ozet}"

            # Spor filtresi
            if cfg_ayarlar.get("sadece_spor_icerik", True):
                skor = spor_skor_hesapla(icerik, SPOR_KELIMELERI)
                if skor < int(cfg_ayarlar.get("spor_filtre_skor_esigi", 1)):
                    continue

            veri = {
                "id": f"newsapi_{hash(link + baslik)}",
                "kaynak_ad": f"{kaynak['ad']} ({kaynak_ad})",
                "kaynak_url": link,
                "kaynak_tur": "NewsAPI",
                "kaynak_kategori": kaynak.get("kategori", "api_haber"),
                "baslik": baslik,
                "ozet": ozet,
                "icerik": icerik,
                "link": link,
                "tarih": tarih.isoformat(),
                "tarih_goster": kisa_tarih(tarih),
                "zaman_farki": zaman_farki(tarih),
                "etkinlik": etkinlik_bilgisi_cikar(icerik, cfg_ayarlar),
                "durum": "aktif"
            }
            veriler.append(veri)
    except Exception as e:
        if cfg_ayarlar.get("debug_modu", False):
            st.warning(f"NewsAPI hatasi ({kaynak['ad']}): {str(e)[:100]}")
    return veriler

def reddit_cek(kaynak, cfg, cfg_ayarlar, limit=25):
    """Reddit'ten gercek zamanli tartisma ve paylasim ceker."""
    veriler = []
    try:
        sorgu = quote(kaynak.get("sorgu", "Amasya spor"))
        url = f"{REDDIT_BASE}?q={sorgu}&limit={limit}&sort=new&t=week"

        headers = {
            'User-Agent': cfg.get("api_anahtarlari", {}).get("reddit_user_agent", "AmasyaSporRadar/4.0")
        }

        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()

        for post in data.get("data", {}).get("children", []):
            p = post.get("data", {})
            baslik = metin_temizle(p.get("title", ""))
            ozet = metin_temizle(p.get("selftext", "")[:500])
            link = f"https://reddit.com{p.get('permalink', '')}"
            tarih_unix = p.get("created_utc", 0)
            tarih = datetime.datetime.fromtimestamp(tarih_unix)
            subreddit = p.get("subreddit", "")
            yazar = p.get("author", "")

            if not baslik:
                continue

            icerik = f"{baslik}. {ozet}"

            # Spor filtresi
            if cfg_ayarlar.get("sadece_spor_icerik", True):
                skor = spor_skor_hesapla(icerik, SPOR_KELIMELERI)
                if skor < int(cfg_ayarlar.get("spor_filtre_skor_esigi", 1)):
                    continue

            veri = {
                "id": f"reddit_{hash(link + baslik)}",
                "kaynak_ad": f"Reddit r/{subreddit}",
                "kaynak_url": f"https://reddit.com/r/{subreddit}",
                "kaynak_tur": "Reddit",
                "kaynak_kategori": kaynak.get("kategori", "reddit"),
                "baslik": baslik,
                "ozet": ozet,
                "icerik": icerik,
                "link": link,
                "tarih": tarih.isoformat(),
                "tarih_goster": kisa_tarih(tarih),
                "zaman_farki": zaman_farki(tarih),
                "etkinlik": etkinlik_bilgisi_cikar(icerik, cfg_ayarlar),
                "durum": "aktif",
                "yazar": yazar,
                "subreddit": subreddit
            }
            veriler.append(veri)
    except Exception as e:
        if cfg_ayarlar.get("debug_modu", False):
            st.warning(f"Reddit hatasi ({kaynak['ad']}): {str(e)[:100]}")
    return veriler

def google_news_cek(kaynak, cfg_ayarlar, limit=15):
    """Google News RSS'ten gercek veri ceker"""
    veriler = []
    try:
        sorgu = quote(kaynak["sorgu"])
        url = f"https://news.google.com/rss/search?q={sorgu}&hl=tr&gl=TR&ceid=TR:tr"
        feed = feedparser.parse(url, request_headers=get_headers())

        for entry in feed.entries[:limit]:
            baslik = metin_temizle(entry.get('title', ''))
            ozet = metin_temizle(entry.get('summary', entry.get('description', '')))
            link = entry.get('link', '')
            tarih_str = entry.get('published', entry.get('updated', ''))
            tarih = tarih_parse(tarih_str)
            icerik = f"{baslik}. {ozet}"

            if cfg_ayarlar.get("sadece_spor_icerik", True):
                skor = spor_skor_hesapla(icerik, SPOR_KELIMELERI)
                if skor < int(cfg_ayarlar.get("spor_filtre_skor_esigi", 1)):
                    continue

            veri = {
                "id": f"gnews_{hash(link + baslik)}",
                "kaynak_ad": kaynak["ad"],
                "kaynak_url": url,
                "kaynak_tur": "Google News",
                "kaynak_kategori": kaynak.get("kategori", "genel"),
                "baslik": baslik,
                "ozet": ozet,
                "icerik": icerik,
                "link": link,
                "tarih": tarih.isoformat(),
                "tarih_goster": kisa_tarih(tarih),
                "zaman_farki": zaman_farki(tarih),
                "etkinlik": etkinlik_bilgisi_cikar(icerik, cfg_ayarlar),
                "durum": "aktif"
            }
            veriler.append(veri)
    except Exception as e:
        if cfg_ayarlar.get("debug_modu", False):
            st.warning(f"Google News hatasi ({kaynak['ad']}): {str(e)[:100]}")
    return veriler

def rss_oku(kaynak, cfg_ayarlar, limit=10):
    veriler = []
    try:
        feed = feedparser.parse(kaynak["url"], request_headers=get_headers())
        for entry in feed.entries[:limit]:
            baslik = metin_temizle(entry.get('title', ''))
            ozet = metin_temizle(entry.get('summary', entry.get('description', '')))
            link = entry.get('link', kaynak["url"])
            tarih_str = entry.get('published', entry.get('updated', ''))
            tarih = tarih_parse(tarih_str)
            icerik = f"{baslik}. {ozet}"

            if cfg_ayarlar.get("sadece_spor_icerik", True):
                skor = spor_skor_hesapla(icerik, SPOR_KELIMELERI)
                if skor < int(cfg_ayarlar.get("spor_filtre_skor_esigi", 1)):
                    continue

            veri = {
                "id": f"rss_{hash(link + baslik)}",
                "kaynak_ad": kaynak["ad"],
                "kaynak_url": kaynak["url"],
                "kaynak_tur": "RSS",
                "kaynak_kategori": kaynak.get("kategori", "genel"),
                "baslik": baslik,
                "ozet": ozet,
                "icerik": icerik,
                "link": link,
                "tarih": tarih.isoformat(),
                "tarih_goster": kisa_tarih(tarih),
                "zaman_farki": zaman_farki(tarih),
                "etkinlik": etkinlik_bilgisi_cikar(icerik, cfg_ayarlar),
                "durum": "aktif"
            }
            veriler.append(veri)
    except Exception as e:
        if cfg_ayarlar.get("debug_modu", False):
            st.warning(f"RSS hatasi ({kaynak['ad']}): {str(e)[:100]}")
    return veriler

def nitter_cek(kaynak, cfg_ayarlar, limit=10):
    veriler = []
    kullanici = kaynak.get("kullanici", "")
    if not kullanici:
        return veriler

    nitter_instances = [
        "https://nitter.pussthecat.org",
        "https://nitter.net",
        "https://nitter.it",
        "https://nitter.cz",
    ]

    for instance in nitter_instances:
        try:
            url = f"{instance}/{kullanici}/rss"
            feed = feedparser.parse(url, request_headers=get_headers())

            if len(feed.entries) > 0:
                for entry in feed.entries[:limit]:
                    baslik = metin_temizle(entry.get('title', ''))
                    ozet = metin_temizle(entry.get('summary', ''))
                    link = entry.get('link', f"https://twitter.com/{kullanici}")
                    tarih_str = entry.get('published', '')
                    tarih = tarih_parse(tarih_str)
                    icerik = f"{baslik}. {ozet}"

                    if cfg_ayarlar.get("sadece_spor_icerik", True):
                        skor = spor_skor_hesapla(icerik, SPOR_KELIMELERI)
                        if skor < int(cfg_ayarlar.get("spor_filtre_skor_esigi", 1)):
                            continue

                    veri = {
                        "id": f"nitter_{hash(link + baslik)}",
                        "kaynak_ad": kaynak["ad"],
                        "kaynak_url": url,
                        "kaynak_tur": "Twitter (Nitter)",
                        "kaynak_kategori": kaynak.get("kategori", "sosyal"),
                        "platform": "twitter",
                        "grup": kaynak.get("grup", ""),
                        "baslik": f"@{kullanici}: {baslik[:100]}",
                        "ozet": ozet,
                        "icerik": icerik,
                        "link": link,
                        "tarih": tarih.isoformat(),
                        "tarih_goster": kisa_tarih(tarih),
                        "zaman_farki": zaman_farki(tarih),
                        "etkinlik": etkinlik_bilgisi_cikar(icerik, cfg_ayarlar),
                        "durum": "aktif"
                    }
                    veriler.append(veri)
                break
        except Exception as e:
            if cfg_ayarlar.get("debug_modu", False):
                st.warning(f"Nitter hatasi ({instance}): {str(e)[:80]}")
            continue
    return veriler

def web_sayfa_oku(kaynak, cfg_ayarlar, limit=15):
    veriler = []
    try:
        response = http_get(kaynak["url"], timeout=cfg_ayarlar.get("kaynak_zaman_asimi_saniye", 15))
        if not response:
            return veriler

        soup = BeautifulSoup(response.text, 'html.parser')
        seciciler = kaynak.get("secici", ".news-item, .post, article, .haber, .duyuru").split(", ")
        bulunan = []
        for secici in seciciler:
            bulunan.extend(soup.select(secici.strip()))

        if not bulunan:
            for link in soup.find_all('a', href=True):
                text = link.get_text(strip=True)
                if len(text) > 20 and len(text) < 200:
                    href = urljoin(kaynak["url"], link['href'])
                    bulunan.append((text, href))

        for item in bulunan[:limit]:
            if isinstance(item, tuple):
                baslik, link = item
                ozet = ""
            else:
                baslik = metin_temizle(item.get_text(separator=' ', strip=True)[:150])
                link_elem = item.find('a') or item.find_parent('a')
                link = urljoin(kaynak["url"], link_elem['href']) if link_elem and link_elem.get('href') else kaynak["url"]
                ozet = metin_temizle(item.get_text(separator=' ', strip=True))

            if not baslik or len(baslik) < 10:
                continue

            icerik = f"{baslik}. {ozet}"

            if cfg_ayarlar.get("sadece_spor_icerik", True):
                skor = spor_skor_hesapla(icerik, SPOR_KELIMELERI)
                if skor < int(cfg_ayarlar.get("spor_filtre_skor_esigi", 1)):
                    continue

            tarih = datetime.datetime.now()
            tarih_elem = item.find(['time', 'span', 'div'], class_=re.compile('date|tarih|time')) if not isinstance(item, tuple) else None
            if tarih_elem:
                tarih = tarih_parse(tarih_elem.get_text())

            veri = {
                "id": f"web_{hash(link + baslik)}",
                "kaynak_ad": kaynak["ad"],
                "kaynak_url": kaynak["url"],
                "kaynak_tur": "Web",
                "kaynak_kategori": kaynak.get("kategori", "genel"),
                "baslik": baslik,
                "ozet": ozet[:300] + "..." if len(ozet) > 300 else ozet,
                "icerik": icerik,
                "link": link,
                "tarih": tarih.isoformat(),
                "tarih_goster": kisa_tarih(tarih),
                "zaman_farki": zaman_farki(tarih),
                "etkinlik": etkinlik_bilgisi_cikar(icerik, cfg_ayarlar),
                "durum": "aktif"
            }
            veriler.append(veri)
    except Exception as e:
        if cfg_ayarlar.get("debug_modu", False):
            st.warning(f"Web hatasi ({kaynak['ad']}): {str(e)[:100]}")
    return veriler

# =============================================================================
# TUM VERILERI TOPLA VE ISLE
# =============================================================================

def tum_verileri_topla(config, progress_callback=None):
    tum_veriler = []
    kaynaklar = config["kaynaklar"]
    cfg_ayarlar = config["ayarlar"]

    aktif_rss = [k for k in kaynaklar["rss_kaynaklari"] if k.get("aktif", True)]
    aktif_api = [k for k in kaynaklar.get("api_kaynaklari", []) if k.get("aktif", True)]
    aktif_web = [k for k in kaynaklar["web_siteleri"] if k.get("aktif", True)]
    aktif_sosyal = [k for k in kaynaklar["sosyal_medya"] if k.get("aktif", True)]
    aktif_etkinlik = [k for k in kaynaklar["etkinlik_kaynaklari"] if k.get("aktif", True)]

    toplam_kaynak = len(aktif_rss) + len(aktif_api) + len(aktif_web) + len(aktif_sosyal) + len(aktif_etkinlik)
    mevcut = 0

    # RSS / Google News
    for kaynak in aktif_rss:
        mevcut += 1
        if progress_callback:
            progress_callback(mevcut, toplam_kaynak, kaynak['ad'])
        if kaynak.get("tur") == "google_news":
            veriler = google_news_cek(kaynak, cfg_ayarlar)
        else:
            veriler = rss_oku(kaynak, cfg_ayarlar)
        tum_veriler.extend(veriler)
        time.sleep(0.3)

    # API kaynaklari (NewsAPI + Reddit)
    for kaynak in aktif_api:
        mevcut += 1
        if progress_callback:
            progress_callback(mevcut, toplam_kaynak, kaynak['ad'])
        if kaynak.get("tur") == "newsapi":
            veriler = newsapi_cek(kaynak, config, cfg_ayarlar)
        elif kaynak.get("tur") == "reddit":
            veriler = reddit_cek(kaynak, config, cfg_ayarlar)
        else:
            veriler = []
        tum_veriler.extend(veriler)
        time.sleep(0.5)

    # Web siteleri
    for kaynak in aktif_web:
        mevcut += 1
        if progress_callback:
            progress_callback(mevcut, toplam_kaynak, kaynak['ad'])
        veriler = web_sayfa_oku(kaynak, cfg_ayarlar)
        tum_veriler.extend(veriler)
        time.sleep(0.3)

    # Sosyal medya (Nitter)
    for kaynak in aktif_sosyal:
        mevcut += 1
        if progress_callback:
            progress_callback(mevcut, toplam_kaynak, kaynak['ad'])
        veriler = nitter_cek(kaynak, cfg_ayarlar)
        tum_veriler.extend(veriler)
        time.sleep(0.3)

    # Etkinlik kaynaklari
    for kaynak in aktif_etkinlik:
        mevcut += 1
        if progress_callback:
            progress_callback(mevcut, toplam_kaynak, kaynak['ad'])
        veriler = web_sayfa_oku(kaynak, cfg_ayarlar)
        tum_veriler.extend(veriler)
        time.sleep(0.3)

    return tum_veriler

def verileri_isle(veriler, config):
    branslar = config["spor_branslari"]
    gruplar = config["taraftar_gruplari"]
    cfg_ayarlar = config["ayarlar"]
    ai_aktif = cfg_ayarlar.get("ai_modul_aktif", False)
    for veri in veriler:
        icerik = veri.get("icerik", "")
        veri["spor_branslari"] = spor_bransi_tespit(icerik, branslar)
        veri["taraftar_gruplari"] = taraftar_grubu_tespit(icerik, gruplar)
        veri["duygu"] = duygu_analizi_basit(icerik, cfg_ayarlar)
        if ai_aktif and icerik and len(icerik) > 100:
            veri["ai_ozet"] = basit_ozetle(icerik, 3)
        else:
            veri["ai_ozet"] = veri.get("ozet", "")
    return veriler

def verileri_birlestir(yeni_veriler, cache, saklama_gun=30):
    mevcut_ids = {v["id"] for v in cache.get("veriler", [])}
    eklenen = 0
    for veri in yeni_veriler:
        if veri["id"] not in mevcut_ids:
            cache["veriler"].append(veri)
            mevcut_ids.add(veri["id"])
            eklenen += 1
    cache["veriler"].sort(key=lambda x: x.get("tarih", ""), reverse=True)
    eski_tarih = (datetime.datetime.now() - datetime.timedelta(days=saklama_gun)).isoformat()
    cache["veriler"] = [v for v in cache["veriler"] if v.get("tarih", "") > eski_tarih]
    cache["son_tarama"] = datetime.datetime.now().isoformat()
    cache["istatistikler"] = {
        "toplam_kayit": len(cache["veriler"]),
        "son_eklenen": eklenen,
        "son_tarama": cache["son_tarama"]
    }
    return cache

# =============================================================================
# STREAMLIT ARAYUZU
# =============================================================================

def sayfa_yapilandir():
    st.set_page_config(
        page_title="Amasya Spor Radar",
        page_icon="futbol",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def sidebar_filtreler(config, cache_veriler):
    with st.sidebar:
        st.title("⚽ Amasya Spor Radar")
        st.caption(f"v{VERSIYON} | API'li Gercek Zamanli Veri")

        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 TARA", type="primary", use_container_width=True):
                return "tara"
        with col2:
            if st.button("🔄 TARA (Cache'siz)", type="secondary", use_container_width=True):
                return "tara_bypass"

        if cache_veriler.get("son_tarama"):
            st.info(f"Son tarama: {zaman_farki(cache_veriler['son_tarama'])}")

        st.divider()
        st.subheader("🔍 Filtreler")

        kategoriler = ["Tumu"] + sorted(list(set(v.get("kaynak_kategori", "genel") for v in cache_veriler.get("veriler", []))))
        secili_kategori = st.selectbox("Kategori", kategoriler, key="filtre_kategori")

        turler = ["Tumu", "Google News", "RSS", "NewsAPI", "Reddit", "Twitter (Nitter)", "Web", "Sosyal Medya"]
        secili_tur = st.selectbox("Kaynak Turu", turler, key="filtre_tur")

        branslar_liste = ["Tumu"] + [b["ad"] for b in config["spor_branslari"]]
        secili_brans = st.selectbox("Spor Bransi", branslar_liste, key="filtre_brans")

        gruplar_liste = ["Tumu"] + [g["ad"] for g in config["taraftar_gruplari"]]
        secili_grup = st.selectbox("Taraftar Grubu", gruplar_liste, key="filtre_grup")

        duygular = ["Tumu", "olumlu", "olumsuz", "notr"]
        secili_duygu = st.selectbox("Duygu Durumu", duygular, key="filtre_duygu")

        st.subheader("📅 Tarih Araligi")
        tarih_secenekleri = ["Tumu", "Son 24 Saat", "Son 3 Gun", "Son 7 Gun", "Son 30 Gun"]
        secili_tarih = st.selectbox("Zaman", tarih_secenekleri, key="filtre_tarih")

        st.subheader("🔎 Arama")
        arama_kelimesi = st.text_input("Kelime ara...", key="arama")

        st.divider()
        st.markdown("Made with care for Amasya")

    return {
        "kategori": secili_kategori,
        "tur": secili_tur,
        "brans": secili_brans,
        "grup": secili_grup,
        "duygu": secili_duygu,
        "tarih": secili_tarih,
        "arama": arama_kelimesi
    }

def verileri_filtrele(veriler, filtreler, config):
    if not veriler:
        return []
    filtrelenmis = veriler.copy()
    if filtreler["kategori"] != "Tumu":
        filtrelenmis = [v for v in filtrelenmis if v.get("kaynak_kategori") == filtreler["kategori"]]
    if filtreler["tur"] != "Tumu":
        filtrelenmis = [v for v in filtrelenmis if v.get("kaynak_tur") == filtreler["tur"]]
    if filtreler["brans"] != "Tumu":
        filtrelenmis = [v for v in filtrelenmis if any(b["ad"] == filtreler["brans"] for b in v.get("spor_branslari", []))]
    if filtreler["grup"] != "Tumu":
        filtrelenmis = [v for v in filtrelenmis if any(g["ad"] == filtreler["grup"] for g in v.get("taraftar_gruplari", []))]
    if filtreler["duygu"] != "Tumu":
        filtrelenmis = [v for v in filtrelenmis if v.get("duygu") == filtreler["duygu"]]
    if filtreler["tarih"] != "Tumu":
        simdi = datetime.datetime.now()
        if filtreler["tarih"] == "Son 24 Saat":
            sinir = simdi - datetime.timedelta(hours=24)
        elif filtreler["tarih"] == "Son 3 Gun":
            sinir = simdi - datetime.timedelta(days=3)
        elif filtreler["tarih"] == "Son 7 Gun":
            sinir = simdi - datetime.timedelta(days=7)
        elif filtreler["tarih"] == "Son 30 Gun":
            sinir = simdi - datetime.timedelta(days=30)
        else:
            sinir = simdi - datetime.timedelta(days=9999)
        filtrelenmis = [v for v in filtrelenmis if tarih_parse(v.get("tarih", simdi.isoformat())) > sinir]
    if filtreler["arama"]:
        arama = filtreler["arama"].lower()
        filtrelenmis = [v for v in filtrelenmis if arama in v.get("baslik", "").lower() or arama in v.get("ozet", "").lower() or arama in v.get("icerik", "").lower()]
    return filtrelenmis

def haber_karti_goster(veri, config):
    ayarlar = config["ayarlar"]
    duygu = veri.get("duygu", "notr")
    duygu_renk = {"olumlu": "🟢", "olumsuz": "🔴", "notr": "⚪"}.get(duygu, "⚪")
    etkinlik = veri.get("etkinlik", {})
    etkinlik_badges = []
    if etkinlik.get("tarih") and ayarlar.get("etkinlik_karti_goster", True):
        etkinlik_badges.append(f"📅 {etkinlik['tarih']}")
    if etkinlik.get("yer"):
        etkinlik_badges.append(f"📍 {etkinlik['yer']}")
    if etkinlik.get("protokol") and ayarlar.get("protokol_vurgula", True):
        etkinlik_badges.append("🏛️ Protokol Katilimi")
    if etkinlik.get("katilimci"):
        etkinlik_badges.append(f"👤 {etkinlik['katilimci']}")
    brans_badges = []
    if ayarlar.get("brans_rozetleri_goster", True):
        for brans in veri.get("spor_branslari", [])[:3]:
            brans_badges.append(f"🏆 {brans['ad']}")
    grup_badges = []
    if ayarlar.get("grup_rozetleri_goster", True):
        for grup in veri.get("taraftar_gruplari", [])[:3]:
            grup_badges.append(f"👥 {grup['ad']}")
    with st.container():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"### [{veri.get('baslik', 'Baslik Yok')}]({veri.get('link', '#')})")
            ozet = veri.get("ai_ozet") or veri.get("ozet", "")
            if ozet:
                st.markdown(f"{ozet[:250]}{'...' if len(ozet) > 250 else ''}")
            badges = []
            if ayarlar.get("kaynak_rozetleri_goster", True):
                badges.append(f"📰 {veri.get('kaynak_ad', 'Bilinmiyor')}")
                badges.append(f"🏷️ {veri.get('kaynak_tur', 'Genel')}")
            badges.append(f"🕐 {veri.get('zaman_farki', 'Bilinmiyor')}")
            if ayarlar.get("duygu_rozetleri_goster", True):
                badges.append(duygu_renk)
            if etkinlik_badges:
                badges.extend(etkinlik_badges)
            if brans_badges:
                badges.extend(brans_badges)
            if grup_badges:
                badges.extend(grup_badges)
            if veri.get("yazar"):
                badges.append(f"✍️ {veri['yazar']}")
            if veri.get("subreddit"):
                badges.append(f"📱 r/{veri['subreddit']}")
            st.markdown(" | ".join(badges))
        with col2:
            st.link_button("🔗 Kaynaga Git", veri.get("link", "#"), use_container_width=True)
            with st.expander("📋 Detaylar"):
                st.write(f"**Kaynak:** {veri.get('kaynak_ad', 'Bilinmiyor')}")
                st.write(f"**Tur:** {veri.get('kaynak_tur', 'Bilinmiyor')}")
                st.write(f"**Kategori:** {veri.get('kaynak_kategori', 'Genel')}")
                st.write(f"**Yayin Tarihi:** {veri.get('tarih_goster', 'Bilinmiyor')}")
                st.write(f"**Duygu:** {duygu}")
                if veri.get("spor_branslari"):
                    st.write(f"**Spor Branslari:** {', '.join(b['ad'] for b in veri['spor_branslari'])}")
                if veri.get("taraftar_gruplari"):
                    st.write(f"**Taraftar Gruplari:** {', '.join(g['ad'] for g in veri['taraftar_gruplari'])}")
                if etkinlik.get("tarih"):
                    st.write(f"**Etkinlik Tarihi:** {etkinlik['tarih']}")
                if etkinlik.get("yer"):
                    st.write(f"**Etkinlik Yeri:** {etkinlik['yer']}")
                if etkinlik.get("katilimci"):
                    st.write(f"**Katilimcilar:** {etkinlik['katilimci']}")
        st.divider()

def istatistik_paneli(veriler, config):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("📊 Toplam", len(veriler))
    with col2:
        st.metric("📰 Google News", len([v for v in veriler if v.get("kaynak_tur") == "Google News"]))
    with col3:
        st.metric("🔌 NewsAPI", len([v for v in veriler if v.get("kaynak_tur") == "NewsAPI"]))
    with col4:
        st.metric("📱 Reddit", len([v for v in veriler if v.get("kaynak_tur") == "Reddit"]))
    with col5:
        st.metric("🐦 Twitter", len([v for v in veriler if v.get("kaynak_tur") == "Twitter (Nitter)"]))
    with col6:
        st.metric("📅 RSS/Web", len([v for v in veriler if v.get("kaynak_tur") in ["RSS", "Web"]]))
    st.divider()

def taraftar_gruplari_paneli(config):
    st.subheader("👥 Taraftar Gruplari")
    gruplar = config["taraftar_gruplari"]
    cols = st.columns(len(gruplar))
    for i, grup in enumerate(gruplar):
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"### {grup['ad']}")
                st.write(f"**Takim:** {grup['takim']}")
                st.write(f"**Renkler:** {', '.join(grup['renkler'])}")
                for platform, kullanici in grup.get("platformlar", {}).items():
                    if platform == "twitter":
                        st.link_button("🐦 Twitter", f"https://twitter.com/{kullanici}")
                    elif platform == "instagram":
                        st.link_button("📷 Instagram", f"https://instagram.com/{kullanici}")
                    elif platform == "facebook":
                        st.link_button("📘 Facebook", f"https://facebook.com/{kullanici}")
    st.divider()

def spor_branslari_paneli(config):
    st.subheader("🏆 Amasya Spor Branslari")
    branslar = config["spor_branslari"]
    for brans in branslar:
        with st.expander(f"{brans['ad']} {'⭐' if brans['oncelik']==1 else ''}"):
            col1, col2 = st.columns([2, 3])
            with col1:
                st.write(f"**Federasyon:** {brans['federasyon']}")
                st.write(f"**Takimlar:** {', '.join(brans['takimlar'])}")
                st.write(f"**Oncelik:** {'Yuksek' if brans['oncelik'] == 1 else 'Normal'}")
            with col2:
                st.info(f"**Amasya Basarilari:** {brans['amasya_basarilari']}")
    st.divider()

def disa_aktar_paneli(veriler, config):
    st.subheader("💾 Disa Aktar")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📄 CSV Indir", use_container_width=True):
            if veriler:
                df = pd.DataFrame(veriler)
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button("CSV Dosyasini Indir", csv, "amasya_spor_veriler.csv", "text/csv")
            else:
                st.warning("Aktarilacak veri yok!")
    with col2:
        if st.button("📊 Excel Indir", use_container_width=True):
            if veriler:
                df = pd.DataFrame(veriler)
                for col in df.columns:
                    if df[col].dtype == 'object':
                        df[col] = df[col].astype(str)
                buffer = io.BytesIO()
                df.to_excel(buffer, index=False, engine='openpyxl')
                st.download_button("Excel Dosyasini Indir", buffer.getvalue(), "amasya_spor_veriler.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.warning("Aktarilacak veri yok!")
    st.divider()

# =============================================================================
# KAPSAMLI AYARLAR PANELI
# =============================================================================

def ayarlar_paneli(config):
    st.header("⚙️ Kapsamli Ayarlar")
    st.info("Tum ayarlari buradan degistirebilirsiniz. API anahtarlarini ekleyerek gercek zamanli veri alabilirsiniz.")

    cfg = config.copy()

    tabs = st.tabs([
        "🔑 API Anahtarlari",
        "🎛️ Genel Ayarlar",
        "📰 Kaynak Yonetimi",
        "👥 Taraftar Gruplari",
        "🏆 Spor Branslari",
        "🤖 AI Modulleri",
        "🔍 Filtre & Arama",
        "📊 Gorunum",
        "💾 Yedekleme"
    ])

    # TAB 1: API Anahtarlari
    with tabs[0]:
        st.subheader("🔑 API Anahtarlari")
        st.warning("API anahtarlari olmadan Google News, RSS ve Reddit calisir. NewsAPI icin key gerekli.")

        api = cfg["api_anahtarlari"]
        api["newsapi"] = st.text_input("NewsAPI Key", value=api.get("newsapi", ""), type="password", help="newsapi.org'dan ucretsiz alabilirsiniz. Gunde 100 istek.")

        st.markdown("""
        **NewsAPI Key Nasil Alinir?**
        1. [newsapi.org](https://newsapi.org) adresine git
        2. "Get API Key" butonuna tikla
        3. E-posta ve sifre ile kaydol (ucretsiz)
        4. Anahtarini kopyala, yukaridaki kutuya yapistir
        5. "TUM AYARLARI KAYDET" butonuna tikla
        """)

        st.divider()
        api["reddit_user_agent"] = st.text_input("Reddit User Agent", value=api.get("reddit_user_agent", "AmasyaSporRadar/4.0"))
        st.caption("Reddit ucretsiz calisir, user agent yeterli.")

    # TAB 2: Genel Ayarlar
    with tabs[1]:
        st.subheader("Uygulama Bilgileri")
        cfg["uygulama_adi"] = st.text_input("Uygulama Adi", value=cfg.get("uygulama_adi", "Amasya Spor Radar"))
        cfg["aciklama"] = st.text_area("Aciklama", value=cfg.get("aciklama", ""))

        st.subheader("Tarama Ayarlari")
        a = cfg["ayarlar"]
        a["otomatik_tarama_aktif"] = st.toggle("Otomatik Tarama (Simulasyon)", value=a.get("otomatik_tarama_aktif", False))
        a["otomatik_tarama_araligi_saat"] = st.number_input("Tarama Araligi (Saat)", min_value=1, max_value=24, value=int(a.get("otomatik_tarama_araligi_saat", 6)))
        a["kaynak_zaman_asimi_saniye"] = st.number_input("Kaynak Zaman Asimi (Saniye)", min_value=5, max_value=60, value=int(a.get("kaynak_zaman_asimi_saniye", 15)))
        a["veri_saklama_gun"] = st.number_input("Veri Saklama Suresi (Gun)", min_value=1, max_value=365, value=int(a.get("veri_saklama_gun", 30)))
        a["cache_bypass"] = st.toggle("Cache Bypass (Her Taramada Yeni Veri)", value=a.get("cache_bypass", False), help="Aciksa her taramada cache'i atlar, sifirdan veri ceker.")

        st.subheader("Bildirim Ayarlari")
        a["bildirim_aktif"] = st.toggle("Bildirim Aktif", value=a.get("bildirim_aktif", False))
        a["bildirim_kanali"] = st.selectbox("Bildirim Kanali", ["yok", "telegram", "email", "webhook"], index=["yok", "telegram", "email", "webhook"].index(a.get("bildirim_kanali", "yok")))

        st.subheader("Dil ve Bolge")
        a["dil"] = st.selectbox("Dil", ["tr", "en"], index=["tr", "en"].index(a.get("dil", "tr")))
        a["zaman_dilimi"] = st.text_input("Zaman Dilimi", value=a.get("zaman_dilimi", "Europe/Istanbul"))

    # TAB 3: Kaynak Yonetimi
    with tabs[2]:
        st.subheader("📡 RSS / Google News Kaynaklari")
        for i, kaynak in enumerate(cfg["kaynaklar"]["rss_kaynaklari"]):
            with st.expander(f"{kaynak['ad']} {'✅' if kaynak.get('aktif') else '❌'}"):
                cols = st.columns([3, 3, 2, 1])
                with cols[0]:
                    kaynak["ad"] = st.text_input(f"Ad {i}", value=kaynak["ad"], key=f"rss_ad_{i}")
                with cols[1]:
                    if kaynak.get("tur") == "google_news":
                        kaynak["sorgu"] = st.text_input(f"Sorgu {i}", value=kaynak.get("sorgu", ""), key=f"rss_sorgu_{i}")
                    else:
                        kaynak["url"] = st.text_input(f"URL {i}", value=kaynak.get("url", ""), key=f"rss_url_{i}")
                with cols[2]:
                    kaynak["kategori"] = st.text_input(f"Kategori {i}", value=kaynak.get("kategori", "genel"), key=f"rss_kat_{i}")
                with cols[3]:
                    kaynak["aktif"] = st.toggle("Aktif", value=kaynak.get("aktif", True), key=f"rss_aktif_{i}")

        st.subheader("🔌 API Kaynaklari (NewsAPI + Reddit)")
        for i, kaynak in enumerate(cfg["kaynaklar"]["api_kaynaklari"]):
            with st.expander(f"{kaynak['ad']} {'✅' if kaynak.get('aktif') else '❌'}"):
                kaynak["ad"] = st.text_input(f"API Ad {i}", value=kaynak["ad"], key=f"api_ad_{i}")
                kaynak["sorgu"] = st.text_input(f"Sorgu {i}", value=kaynak.get("sorgu", ""), key=f"api_sorgu_{i}")
                kaynak["tur"] = st.selectbox(f"Tur {i}", ["newsapi", "reddit"], index=["newsapi", "reddit"].index(kaynak.get("tur", "newsapi")), key=f"api_tur_{i}")
                kaynak["kategori"] = st.text_input(f"Kategori {i}", value=kaynak.get("kategori", "api_haber"), key=f"api_kat_{i}")
                kaynak["aktif"] = st.toggle(f"Aktif {i}", value=kaynak.get("aktif", True), key=f"api_aktif_{i}")

        st.subheader("🌐 Web Siteleri (Bot Korumali - Varsayilan Kapali)")
        for i, kaynak in enumerate(cfg["kaynaklar"]["web_siteleri"]):
            with st.expander(f"{kaynak['ad']} {'✅' if kaynak.get('aktif') else '❌'}"):
                kaynak["ad"] = st.text_input(f"Web Ad {i}", value=kaynak["ad"], key=f"web_ad_{i}")
                kaynak["url"] = st.text_input(f"Web URL {i}", value=kaynak["url"], key=f"web_url_{i}")
                kaynak["aktif"] = st.toggle(f"Web Aktif {i}", value=kaynak.get("aktif", False), key=f"web_aktif_{i}")

        st.subheader("📱 Sosyal Medya (Nitter)")
        for i, kaynak in enumerate(cfg["kaynaklar"]["sosyal_medya"]):
            with st.expander(f"{kaynak['ad']} {'✅' if kaynak.get('aktif') else '❌'}"):
                kaynak["ad"] = st.text_input(f"Sosyal Ad {i}", value=kaynak["ad"], key=f"sos_ad_{i}")
                kaynak["kullanici"] = st.text_input(f"Kullanici {i}", value=kaynak.get("kullanici", ""), key=f"sos_kul_{i}")
                kaynak["aktif"] = st.toggle(f"Sosyal Aktif {i}", value=kaynak.get("aktif", True), key=f"sos_aktif_{i}")

        st.subheader("➕ Yeni Kaynak Ekle")
        yeni_tur = st.selectbox("Kaynak Turu", ["google_news", "newsapi", "reddit", "rss", "web", "nitter"], key="yeni_tur")
        yeni_ad = st.text_input("Kaynak Adi", key="yeni_ad")
        yeni_sorgu = st.text_input("Sorgu / URL / Kullanici", key="yeni_sorgu")
        if st.button("Ekle", key="kaynak_ekle"):
            if yeni_ad and yeni_sorgu:
                if yeni_tur == "google_news":
                    cfg["kaynaklar"]["rss_kaynaklari"].append({"ad": yeni_ad, "tur": "google_news", "sorgu": yeni_sorgu, "aktif": True, "kategori": "genel_haber"})
                elif yeni_tur == "newsapi":
                    cfg["kaynaklar"]["api_kaynaklari"].append({"ad": yeni_ad, "tur": "newsapi", "sorgu": yeni_sorgu, "aktif": True, "kategori": "api_haber"})
                elif yeni_tur == "reddit":
                    cfg["kaynaklar"]["api_kaynaklari"].append({"ad": yeni_ad, "tur": "reddit", "sorgu": yeni_sorgu, "aktif": True, "kategori": "reddit"})
                elif yeni_tur == "rss":
                    cfg["kaynaklar"]["rss_kaynaklari"].append({"ad": yeni_ad, "url": yeni_sorgu, "tur": "rss", "aktif": True, "kategori": "genel_haber"})
                elif yeni_tur == "web":
                    cfg["kaynaklar"]["web_siteleri"].append({"ad": yeni_ad, "url": yeni_sorgu, "tur": "web", "aktif": True, "kategori": "genel", "secici": ".post, .news-item, article"})
                elif yeni_tur == "nitter":
                    cfg["kaynaklar"]["sosyal_medya"].append({"ad": yeni_ad, "kullanici": yeni_sorgu, "tur": "nitter", "platform": "twitter", "aktif": True, "kategori": "taraftar", "grup": ""})
                st.success(f"{yeni_ad} eklendi! Ayarlari kaydetmeyi unutmayin.")

    # TAB 4: Taraftar Gruplari
    with tabs[3]:
        st.subheader("Taraftar Grubu Yonetimi")
        for i, grup in enumerate(cfg["taraftar_gruplari"]):
            with st.expander(f"{grup['ad']} {'⭐' if grup['oncelik']==1 else ''}"):
                grup["ad"] = st.text_input(f"Grup Ad {i}", value=grup["ad"], key=f"tg_ad_{i}")
                grup["kisa_ad"] = st.text_input(f"Kisa Ad {i}", value=grup["kisa_ad"], key=f"tg_kisa_{i}")
                grup["renkler"] = st.text_input(f"Renkler (virgulle) {i}", value=", ".join(grup.get("renkler", [])), key=f"tg_renk_{i}").split(", ")
                grup["takim"] = st.text_input(f"Takim {i}", value=grup["takim"], key=f"tg_takim_{i}")
                grup["oncelik"] = st.number_input(f"Oncelik {i}", min_value=1, max_value=5, value=int(grup.get("oncelik", 2)), key=f"tg_onc_{i}")
                grup["aktif"] = st.toggle(f"Aktif {i}", value=grup.get("aktif", True), key=f"tg_aktif_{i}")
                st.write("Platformlar:")
                for plat in ["twitter", "instagram", "facebook"]:
                    grup["platformlar"][plat] = st.text_input(f"{plat.capitalize()} {i}", value=grup.get("platformlar", {}).get(plat, ""), key=f"tg_{plat}_{i}")
        st.subheader("➕ Yeni Taraftar Grubu Ekle")
        yeni_tg_ad = st.text_input("Grup Adi", key="yeni_tg_ad")
        yeni_tg_kisa = st.text_input("Kisa Ad (bosluk yok)", key="yeni_tg_kisa")
        if st.button("Grup Ekle", key="tg_ekle"):
            if yeni_tg_ad and yeni_tg_kisa:
                cfg["taraftar_gruplari"].append({
                    "ad": yeni_tg_ad, "kisa_ad": yeni_tg_kisa, "renkler": ["Yesil", "Siyah"],
                    "takim": "Amasyaspor FK", "platformlar": {"twitter": yeni_tg_kisa, "instagram": yeni_tg_kisa, "facebook": yeni_tg_kisa},
                    "aktif": True, "oncelik": 2
                })
                st.success(f"{yeni_tg_ad} eklendi!")

    # TAB 5: Spor Branslari
    with tabs[4]:
        st.subheader("Spor Bransi Yonetimi")
        for i, brans in enumerate(cfg["spor_branslari"]):
            with st.expander(f"{brans['ad']} {'⭐' if brans['oncelik']==1 else ''}"):
                brans["ad"] = st.text_input(f"Brans Ad {i}", value=brans["ad"], key=f"br_ad_{i}")
                brans["kisa_ad"] = st.text_input(f"Kisa Ad {i}", value=brans["kisa_ad"], key=f"br_kisa_{i}")
                brans["federasyon"] = st.text_input(f"Federasyon {i}", value=brans["federasyon"], key=f"br_fed_{i}")
                brans["takimlar"] = st.text_input(f"Takimlar (virgulle) {i}", value=", ".join(brans.get("takimlar", [])), key=f"br_takim_{i}").split(", ")
                brans["oncelik"] = st.number_input(f"Oncelik {i}", min_value=1, max_value=5, value=int(brans.get("oncelik", 2)), key=f"br_onc_{i}")
                brans["amasya_basarilari"] = st.text_area(f"Amasya Basarilari {i}", value=brans.get("amasya_basarilari", ""), key=f"br_bas_{i}")
        st.subheader("➕ Yeni Spor Bransi Ekle")
        yeni_br_ad = st.text_input("Brans Adi", key="yeni_br_ad")
        yeni_br_kisa = st.text_input("Kisa Ad", key="yeni_br_kisa")
        if st.button("Brans Ekle", key="br_ekle"):
            if yeni_br_ad and yeni_br_kisa:
                cfg["spor_branslari"].append({
                    "ad": yeni_br_ad, "kisa_ad": yeni_br_kisa, "takimlar": [f"Amasya {yeni_br_ad}"],
                    "federasyon": "TFF", "oncelik": 2, "amasya_basarilari": ""
                })
                st.success(f"{yeni_br_ad} eklendi!")

    # TAB 6: AI Modulleri
    with tabs[5]:
        st.subheader("🤖 Yapay Zeka Modulleri")
        a = cfg["ayarlar"]
        a["ai_modul_aktif"] = st.toggle("AI Modulunu Aktif Et", value=a.get("ai_modul_aktif", False))
        for modul_adi, modul in cfg["ai_modulleri"].items():
            with st.expander(f"{modul_adi.capitalize()}"):
                modul["aktif"] = st.toggle(f"{modul_adi} Aktif", value=modul.get("aktif", False), key=f"ai_{modul_adi}")
                modul["aciklama"] = st.text_area(f"Aciklama", value=modul.get("aciklama", ""), key=f"ai_acik_{modul_adi}")
                if modul_adi == "ozetleyici":
                    modul["parametreler"]["max_cumle"] = st.number_input("Max Cumle", min_value=1, max_value=10, value=int(modul["parametreler"].get("max_cumle", 3)), key=f"ai_max_{modul_adi}")

    # TAB 7: Filtre & Arama
    with tabs[6]:
        st.subheader("🔍 Icerik Filtreleme")
        a = cfg["ayarlar"]
        a["sadece_spor_icerik"] = st.toggle("Sadece Spor Icerigi Goster", value=a.get("sadece_spor_icerik", True))
        a["spor_filtre_skor_esigi"] = st.number_input("Spor Filtre Skor Esigi", min_value=0, max_value=10, value=int(a.get("spor_filtre_skor_esigi", 1)))
        a["etkinlik_sadece_spor"] = st.toggle("Etkinlikler Sadece Spor Olsun", value=a.get("etkinlik_sadece_spor", True))
        cfg["anahtar_kelimeler"] = st.text_area("Anahtar Kelimeler (virgulle)", value=", ".join(cfg.get("anahtar_kelimeler", [])), height=100).split(", ")
        a["protokol_kelime_listesi"] = st.text_area("Protokol Kelimeleri (virgulle)", value=a.get("protokol_kelime_listesi", "vali,belediye baskani"), height=60)
        a["yer_kelime_listesi"] = st.text_area("Yer Kelimeleri (virgulle)", value=a.get("yer_kelime_listesi", "amasya,stadyum"), height=60)
        a["olumlu_duygu_kelimeleri"] = st.text_area("Olumlu Kelimeler (virgulle)", value=a.get("olumlu_duygu_kelimeleri", "basari,zafer"), height=60)
        a["olumsuz_duygu_kelimeleri"] = st.text_area("Olumsuz Kelimeler (virgulle)", value=a.get("olumsuz_duygu_kelimeleri", "maglup,kaybetti"), height=60)

    # TAB 8: Gorunum
    with tabs[7]:
        st.subheader("🎨 Gorunum Ayarlari")
        a = cfg["ayarlar"]
        a["sayfa_basligi"] = st.text_input("Sayfa Basligi", value=a.get("sayfa_basligi", "Amasya Spor Radar"))
        a["favicon"] = st.selectbox("Favicon", ["futbol", "trophy", "fire", "star", "zap"], index=["futbol", "trophy", "fire", "star", "zap"].index(a.get("favicon", "futbol")))
        a["gorunum_tema"] = st.selectbox("Tema", ["acik", "koyu", "otomatik"], index=["acik", "koyu", "otomatik"].index(a.get("gorunum_tema", "acik")))
        a["sayfa_basina_kayit"] = st.number_input("Sayfa Basina Kayit", min_value=5, max_value=100, value=int(a.get("sayfa_basina_kayit", 20)))
        a["kaynak_rozetleri_goster"] = st.toggle("Kaynak Rozetleri", value=a.get("kaynak_rozetleri_goster", True))
        a["duygu_rozetleri_goster"] = st.toggle("Duygu Rozetleri", value=a.get("duygu_rozetleri_goster", True))
        a["brans_rozetleri_goster"] = st.toggle("Brans Rozetleri", value=a.get("brans_rozetleri_goster", True))
        a["grup_rozetleri_goster"] = st.toggle("Grup Rozetleri", value=a.get("grup_rozetleri_goster", True))
        a["etkinlik_karti_goster"] = st.toggle("Etkinlik Karti Goster", value=a.get("etkinlik_karti_goster", True))
        a["protokol_vurgula"] = st.toggle("Protokol Vurgula", value=a.get("protokol_vurgula", True))
        a["disa_aktar_format"] = st.selectbox("Varsayilan Format", ["excel", "csv"], index=["excel", "csv"].index(a.get("disa_aktar_format", "excel")))

    # TAB 9: Yedekleme
    with tabs[8]:
        st.subheader("💾 Config Yedekleme")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(config_indir(cfg), unsafe_allow_html=True)
        with col2:
            uploaded = st.file_uploader("Config Yukle", type=["json"])
            if uploaded is not None:
                if st.button("Yuklenen Config'i Uygula"):
                    if config_yukle(uploaded):
                        st.success("Config yuklendi! Sayfa yenileniyor...")
                        st.rerun()
        st.subheader("🗑️ Veri Yonetimi")
        if st.button("🗑️ Onbellegi Temizle", type="secondary"):
            if os.path.exists(CACHE_DOSYA):
                os.remove(CACHE_DOSYA)
            st.success("Onbellek temizlendi!")
        if st.button("🔄 Varsayilan Ayarlara Don", type="secondary"):
            with open(CONFIG_DOSYA, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
            st.success("Varsayilan ayarlara donuldu!")
            st.rerun()
        a["debug_modu"] = st.toggle("Debug Modu", value=a.get("debug_modu", False))
        if a.get("debug_modu"):
            st.json(cfg)

    st.divider()
    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("💾 TUM AYARLARI KAYDET", type="primary", use_container_width=True):
            if config_yaz(cfg):
                st.success("Ayarlar kaydedildi!")
                st.balloons()
                time.sleep(1)
                st.rerun()
    with col_cancel:
        if st.button("❌ Iptal", use_container_width=True):
            st.rerun()
    return cfg

# =============================================================================
# TARAMA EKRANI VE ANA PROGRAM
# =============================================================================

def tarama_ekrani(config, bypass_cache=False):
    st.title("🔄 Kaynaklar Taraniyor...")
    progress_bar = st.progress(0)
    durum_text = st.empty()

    def progress_callback(mevcut, toplam, mesaj):
        progress = int((mevcut / toplam) * 100) if toplam > 0 else 0
        progress_bar.progress(min(progress, 100))
        durum_text.text(f"{mevcut}/{toplam} - {mesaj}")

    yeni_veriler = tum_verileri_topla(config, progress_callback)
    durum_text.text("Veriler isleniyor...")
    yeni_veriler = verileri_isle(yeni_veriler, config)

    if bypass_cache:
        cache = {"veriler": [], "son_tarama": None, "istatistikler": {}}
    else:
        cache = cache_oku()

    saklama = int(config["ayarlar"].get("veri_saklama_gun", 30))
    cache = verileri_birlestir(yeni_veriler, cache, saklama)
    cache_yaz(cache)

    progress_bar.empty()
    durum_text.empty()

    st.success(f"Tarama tamamlandi! {cache['istatistikler']['son_eklenen']} yeni kayit bulundu.")
    st.info(f"Toplam kayit: {cache['istatistikler']['toplam_kayit']} | API kaynaklari aktif: {'✅ NewsAPI' if config['api_anahtarlari'].get('newsapi') else '❌ NewsAPI'} | {'✅ Reddit' if True else '❌ Reddit'}")
    time.sleep(2)
    st.rerun()

def ana_ekran(config, cache):
    st.title(f"⚽ {config.get('uygulama_adi', 'Amasya Spor Radar')}")
    st.caption(f"v{VERSIYON} | {config.get('aciklama', '')}")

    # API durumu banner
    api_key = config.get("api_anahtarlari", {}).get("newsapi", "")
    if not api_key:
        st.warning("⚠️ NewsAPI anahtari bulunamadi! Gercek zamanli haberler icin [newsapi.org](https://newsapi.org) adresinden ucretsiz API key alin. Ayarlar > API Anahtarlari sekmesinden ekleyin.")
    else:
        st.success("✅ NewsAPI baglantisi aktif! Gercek zamanli haberler cekiliyor.")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📰 Haberler & Etkinlikler", 
        "👥 Taraftar Gruplari", 
        "🏆 Spor Branslari",
        "📊 Istatistikler",
        "💾 Disa Aktar",
        "⚙️ Ayarlar"
    ])

    veriler = cache.get("veriler", [])

    with tab1:
        if not veriler:
            st.info("Henuz veri yok. Lutfen soldaki 'TARA' veya 'TARA (Cache\'siz)' butonuna basin.")
            st.markdown("""
            ### Baslangic
            1. **NewsAPI Key** al (ucretsiz): [newsapi.org](https://newsapi.org)
            2. Ayarlar > API Anahtarlari > NewsAPI Key'i yapistir
            3. Soldaki **"TARA"** butonuna bas
            4. Gercek zamanli haberler ve tartismalar gelecek
            """)
        else:
            istatistik_paneli(veriler, config)
            filtreler = {
                "kategori": st.session_state.get("filtre_kategori", "Tumu"),
                "tur": st.session_state.get("filtre_tur", "Tumu"),
                "brans": st.session_state.get("filtre_brans", "Tumu"),
                "grup": st.session_state.get("filtre_grup", "Tumu"),
                "duygu": st.session_state.get("filtre_duygu", "Tumu"),
                "tarih": st.session_state.get("filtre_tarih", "Tumu"),
                "arama": st.session_state.get("arama", "")
            }
            filtrelenmis = verileri_filtrele(veriler, filtreler, config)
            st.subheader(f"Sonuclar ({len(filtrelenmis)} kayit)")
            if not filtrelenmis:
                st.warning("Secili filtrelere uygun kayit bulunamadi.")
            else:
                sayfa_basina = int(config["ayarlar"].get("sayfa_basina_kayit", 20))
                toplam_sayfa = max(1, (len(filtrelenmis) + sayfa_basina - 1) // sayfa_basina)
                sayfa = st.number_input("Sayfa", min_value=1, max_value=toplam_sayfa, value=1, key="sayfa")
                baslangic = (sayfa - 1) * sayfa_basina
                bitis = min(baslangic + sayfa_basina, len(filtrelenmis))
                st.caption(f"Gosterilen: {baslangic + 1}-{bitis} / Toplam: {len(filtrelenmis)}")
                for veri in filtrelenmis[baslangic:bitis]:
                    haber_karti_goster(veri, config)

    with tab2:
        taraftar_gruplari_paneli(config)
        st.subheader("Taraftar Gruplari Ilgili Haberler")
        for grup in config["taraftar_gruplari"]:
            grup_haberleri = [v for v in veriler if any(g["ad"] == grup["ad"] for g in v.get("taraftar_gruplari", []))]
            if grup_haberleri:
                with st.expander(f"{grup['ad']} - {len(grup_haberleri)} haber"):
                    for haber in grup_haberleri[:5]:
                        st.markdown(f"- [{haber.get('baslik', '')}]({haber.get('link', '#')}) - {haber.get('kaynak_ad', '')}")

    with tab3:
        spor_branslari_paneli(config)
        st.subheader("Spor Branslari Ilgili Haberler")
        for brans in config["spor_branslari"]:
            brans_haberleri = [v for v in veriler if any(b["ad"] == brans["ad"] for b in v.get("spor_branslari", []))]
            if brans_haberleri:
                with st.expander(f"{brans['ad']} - {len(brans_haberleri)} haber"):
                    for haber in brans_haberleri[:5]:
                        st.markdown(f"- [{haber.get('baslik', '')}]({haber.get('link', '#')}) - {haber.get('kaynak_ad', '')}")

    with tab4:
        st.subheader("Genel Istatistikler")
        if veriler:
            kaynak_dagilimi = defaultdict(int)
            for v in veriler:
                kaynak_dagilimi[v.get("kaynak_ad", "Bilinmiyor")] += 1
            st.write("**Kaynak Dagilimi:**")
            for kaynak, sayi in sorted(kaynak_dagilimi.items(), key=lambda x: x[1], reverse=True)[:10]:
                st.write(f"- {kaynak}: {sayi} kayit")
            tur_dagilimi = defaultdict(int)
            for v in veriler:
                tur_dagilimi[v.get("kaynak_tur", "Bilinmiyor")] += 1
            st.write("**Kaynak Turu Dagilimi:**")
            for tur, sayi in sorted(tur_dagilimi.items(), key=lambda x: x[1], reverse=True):
                st.write(f"- {tur}: {sayi}")
            duygu_dagilimi = defaultdict(int)
            for v in veriler:
                duygu_dagilimi[v.get("duygu", "notr")] += 1
            st.write("**Duygu Dagilimi:**")
            for duygu, sayi in duygu_dagilimi.items():
                emoji = {"olumlu": "🟢", "olumsuz": "🔴", "notr": "⚪"}.get(duygu, "⚪")
                st.write(f"- {emoji} {duygu}: {sayi}")
            brans_dagilimi = defaultdict(int)
            for v in veriler:
                for b in v.get("spor_branslari", []):
                    brans_dagilimi[b["ad"]] += 1
            if brans_dagilimi:
                st.write("**Brans Dagilimi:**")
                for brans, sayi in sorted(brans_dagilimi.items(), key=lambda x: x[1], reverse=True):
                    st.write(f"- {brans}: {sayi} haber")
        else:
            st.info("Henuz istatistik icin yeterli veri yok. Tarama yapin.")

    with tab5:
        disa_aktar_paneli(veriler, config)

    with tab6:
        ayarlar_paneli(config)

def main():
    sayfa_yapilandir()
    config = config_oku()
    if not config:
        st.error("Config.json bulunamadi! Varsayilan ayarlar olusturuluyor...")
        config = DEFAULT_CONFIG.copy()
        config_yaz(config)

    cache = cache_oku()
    sidebar_sonuc = sidebar_filtreler(config, cache)

    if sidebar_sonuc == "tara":
        tarama_ekrani(config, bypass_cache=False)
        return
    elif sidebar_sonuc == "tara_bypass":
        tarama_ekrani(config, bypass_cache=True)
        return

    ana_ekran(config, cache)

if __name__ == "__main__":
    main()
