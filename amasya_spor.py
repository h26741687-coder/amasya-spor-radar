#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Amasya Spor Radar v2.0
Tarih uyumu | Spor filtresi | Kapsamli ayarlar paneli
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
from dateutil import parser as date_parser
from urllib.parse import urljoin
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
VERSIYON = "2.0"

# Spor anahtar kelimeleri (icerik filtreleme icin)
SPOR_KELIMELERI = [
    "spor", "futbol", "voleybol", "basketbol", "gures", "hentbol", "atletizm",
    "yuzme", "okculuk", "judo", "taekwondo", "tenis", "masa tenisi", "badminton",
    "boks", "kick boks", "karate", "wushu", "halter", "gures", "gures",
    "triatlon", "maraton", "kosu", "atletizm", "jimnastik", "cimnastik",
    "buz pateni", "hokey", "ragbi", "kriket", "beyzbol", "softbol",
    "amasyaspor", "amasyaspor fk", "yesil simsekler", "sehzadeler",
    "taraftar", "mac", "musabaka", "turnuva", "sampiyona", "lig", "kupa",
    "federasyon", "tff", "tvf", "tbf", "tgf", "taf", "tyf", "tokf", "tjf", "ttf", "thf",
    "gsb", "genclik ve spor", "belediyespor", "universitesi spor",
    "stadyum", "spor salonu", "spor kompleksi", "stad", "saha", "pist",
    "antrenor", "teknik direktor", "transfer", "gol", "asist", "sampiyon",
    "basari", "madalya", "kupa", "kazan", "maglubiyet", "galibiyet", "beraberlik",
    "hakem", "takim", "oyuncu", "sporcu", "mili takim", "alt yapı", "altyapi"
]

# Etkinlik spor kelimeleri (sadece spor etkinliklerini yakalamak icin)
ETKINLIK_SPOR_KELIMELERI = [
    "mac", "musabaka", "turnuva", "sampiyona", "lig", "kupa", "futbol", "voleybol",
    "basketbol", "gures", "yarisma", "etkinlik", "spor", "karsilasma", "derbi",
    "spor salonu", "stadyum", "stad", "saha", "antrenman", "kamp", "davet",
    "acilis", "kapanis", "toren", "odul", "madalya", "basari"
]

# Varsayilan config
DEFAULT_CONFIG = {
    "uygulama_adi": "Amasya Spor Radar",
    "versiyon": "2.0",
    "aciklama": "Amasya'daki tum sportif faaliyetleri takip eden istihbarat sistemi",
    "kaynaklar": {
        "rss_kaynaklari": [
            {"ad": "Amasya Gazetesi - Spor", "url": "https://www.amasyagazetesi.com.tr/rss/spor", "tur": "rss", "aktif": True, "kategori": "yerel_haber"},
            {"ad": "Amasya Haber", "url": "https://www.amasyahaber.com/rss", "tur": "rss", "aktif": True, "kategori": "yerel_haber"},
            {"ad": "Amasya'nin Sesi", "url": "https://www.amasyaninsesi.com.tr/rss", "tur": "rss", "aktif": True, "kategori": "yerel_haber"},
            {"ad": "Amasya Son Haber", "url": "https://www.amasyasonhaber.com/rss", "tur": "rss", "aktif": True, "kategori": "yerel_haber"},
            {"ad": "TRT Haber - Amasya", "url": "https://www.trthaber.com/amasya.rss", "tur": "rss", "aktif": True, "kategori": "genel_haber"},
            {"ad": "Hurriyet - Amasya", "url": "https://www.hurriyet.com.tr/rss/amasya", "tur": "rss", "aktif": True, "kategori": "genel_haber"},
            {"ad": "Sporx - Amasya", "url": "https://www.sporx.com/rss/amasya", "tur": "rss", "aktif": True, "kategori": "spor_haber"}
        ],
        "web_siteleri": [
            {"ad": "TFF - Amasya Il Temsilciligi", "url": "https://www.tff.org/Default.aspx?pageID=527&ilID=5", "tur": "web", "aktif": True, "kategori": "federasyon", "secici": ".news-item, .haber-item, .duyuru-item"},
            {"ad": "Genclik ve Spor Il Mudurlugu", "url": "https://amasya.gsb.gov.tr/", "tur": "web", "aktif": True, "kategori": "resmi", "secici": ".news-item, .announcement, .duyuru, .haber"},
            {"ad": "Amasya Belediyesi - Spor", "url": "https://www.amasya.bel.tr/haberler/spor", "tur": "web", "aktif": True, "kategori": "belediye", "secici": ".news-item, .post, .haber, article"},
            {"ad": "Amasya Valiligi - Duyurular", "url": "https://www.amasya.gov.tr/duyurular", "tur": "web", "aktif": True, "kategori": "resmi", "secici": ".announcement, .duyuru, .news-item"},
            {"ad": "TVF - Amasya", "url": "https://www.tvf.org.tr/", "tur": "web", "aktif": True, "kategori": "federasyon", "secici": ".news-item, .haber"},
            {"ad": "Amasyaspor FK", "url": "https://www.amasyasporfk.com/", "tur": "web", "aktif": True, "kategori": "kulup", "secici": ".news-item, .post, .haber, article"},
            {"ad": "Amasya Gazetesi Web", "url": "https://www.amasyagazetesi.com.tr/kategori/spor/", "tur": "web", "aktif": True, "kategori": "yerel_haber", "secici": ".post, .news-item, article, .haber"},
            {"ad": "Amasya Haber Web", "url": "https://www.amasyahaber.com/spor/", "tur": "web", "aktif": True, "kategori": "yerel_haber", "secici": ".post, .news-item, article, .haber"},
            {"ad": "Amasya'nin Sesi Web", "url": "https://www.amasyaninsesi.com.tr/kategori/spor/", "tur": "web", "aktif": True, "kategori": "yerel_haber", "secici": ".post, .news-item, article, .haber"},
            {"ad": "Amasya Son Haber Web", "url": "https://www.amasyasonhaber.com/spor/", "tur": "web", "aktif": True, "kategori": "yerel_haber", "secici": ".post, .news-item, article, .haber"},
            {"ad": "Hurriyet - Amasya Spor", "url": "https://www.hurriyet.com.tr/arama/?q=amasya+spor", "tur": "web", "aktif": True, "kategori": "genel_haber", "secici": ".news-item, .post, article"},
            {"ad": "Milliyet - Amasya Spor", "url": "https://www.milliyet.com.tr/arama/?q=amasya+spor", "tur": "web", "aktif": True, "kategori": "genel_haber", "secici": ".news-item, .post, article"},
            {"ad": "Sporx - Amasya", "url": "https://www.sporx.com/arama/?q=amasya", "tur": "web", "aktif": True, "kategori": "spor_haber", "secici": ".news-item, .post, article"},
            {"ad": "Fanatik - Amasya", "url": "https://www.fanatik.com.tr/arama/?q=amasya", "tur": "web", "aktif": True, "kategori": "spor_haber", "secici": ".news-item, .post, article"},
            {"ad": "NTV Spor - Amasya", "url": "https://www.ntvspor.net/arama/?q=amasya", "tur": "web", "aktif": True, "kategori": "spor_haber", "secici": ".news-item, .post, article"},
            {"ad": "TRT Spor - Amasya", "url": "https://www.trtspor.com.tr/arama/?q=amasya", "tur": "web", "aktif": True, "kategori": "spor_haber", "secici": ".news-item, .post, article"},
            {"ad": "Amasya Universitesi - Spor", "url": "https://www.amasya.edu.tr/tr/duyurular", "tur": "web", "aktif": True, "kategori": "universite", "secici": ".duyuru, .announcement, .news-item"}
        ],
        "sosyal_medya": [
            {"ad": "Yesil Simsekler Twitter", "url": "https://twitter.com/yesilsimsekler", "tur": "sosyal", "platform": "twitter", "aktif": True, "kategori": "taraftar", "grup": "Yesil Simsekler"},
            {"ad": "Sehzadeler Twitter", "url": "https://twitter.com/sehzadeler", "tur": "sosyal", "platform": "twitter", "aktif": True, "kategori": "taraftar", "grup": "Sehzadeler"},
            {"ad": "Amasyaspor FK Twitter", "url": "https://twitter.com/amasyasporfk", "tur": "sosyal", "platform": "twitter", "aktif": True, "kategori": "kulup", "grup": "Amasyaspor FK"},
            {"ad": "Amasya GSB Twitter", "url": "https://twitter.com/amasya_gsb", "tur": "sosyal", "platform": "twitter", "aktif": True, "kategori": "resmi", "grup": "GSB Amasya"},
            {"ad": "Amasya Belediyesi Twitter", "url": "https://twitter.com/amasyabelediye", "tur": "sosyal", "platform": "twitter", "aktif": True, "kategori": "belediye", "grup": "Amasya Belediyesi"},
            {"ad": "Yesil Simsekler Instagram", "url": "https://www.instagram.com/yesilsimsekler/", "tur": "sosyal", "platform": "instagram", "aktif": True, "kategori": "taraftar", "grup": "Yesil Simsekler"},
            {"ad": "Sehzadeler Instagram", "url": "https://www.instagram.com/sehzadeler/", "tur": "sosyal", "platform": "instagram", "aktif": True, "kategori": "taraftar", "grup": "Sehzadeler"},
            {"ad": "Amasyaspor FK Instagram", "url": "https://www.instagram.com/amasyasporfk/", "tur": "sosyal", "platform": "instagram", "aktif": True, "kategori": "kulup", "grup": "Amasyaspor FK"},
            {"ad": "Amasya GSB Instagram", "url": "https://www.instagram.com/amasya.gsb/", "tur": "sosyal", "platform": "instagram", "aktif": True, "kategori": "resmi", "grup": "GSB Amasya"}
        ],
        "etkinlik_kaynaklari": [
            {"ad": "TFF Musabaka Takvimi", "url": "https://www.tff.org/Default.aspx?pageID=1428", "tur": "etkinlik", "aktif": True, "kategori": "musabaka"},
            {"ad": "TVF Musabaka Takvimi", "url": "https://www.tvf.org.tr/fikstur/", "tur": "etkinlik", "aktif": True, "kategori": "musabaka"},
            {"ad": "Amasya Belediyesi Etkinlikler", "url": "https://www.amasya.bel.tr/etkinlikler", "tur": "etkinlik", "aktif": True, "kategori": "etkinlik"},
            {"ad": "Amasya Valiligi Etkinlikler", "url": "https://www.amasya.gov.tr/etkinlikler", "tur": "etkinlik", "aktif": True, "kategori": "etkinlik"},
            {"ad": "GSB Etkinlik Takvimi", "url": "https://etkinlik.gov.tr/", "tur": "etkinlik", "aktif": True, "kategori": "etkinlik"}
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
        {"ad": "Gures", "kisa_ad": "gures", "takimlar": ["Amasya Gures Takimi"], "federasyon": "TGF", "oncelik": 1, "amasya_basarilari": "Geleneksel yagli guresler, okul sporlari"},
        {"ad": "Okculuk", "kisa_ad": "okculuk", "takimlar": ["Amasya Okculuk"], "federasyon": "TOKF", "oncelik": 2, "amasya_basarilari": "Genclik ve spor mudurlugu altyapi basarilari"},
        {"ad": "Atletizm", "kisa_ad": "atletizm", "takimlar": ["Amasya Atletizm"], "federasyon": "TAF", "oncelik": 2, "amasya_basarilari": "Bolgesel yarisamalarda madalyalar"},
        {"ad": "Yuzme", "kisa_ad": "yuzme", "takimlar": ["Amasya Yuzme"], "federasyon": "TYF", "oncelik": 2, "amasya_basarilari": "Genclik kategorilerinde basarilar"},
        {"ad": "Judo", "kisa_ad": "judo", "takimlar": ["Amasya Judo"], "federasyon": "TJF", "oncelik": 2, "amasya_basarilari": "Okul sporlari ve genclik basarilari"},
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

    # Once spor etkinlik mi kontrol et
    spor_skor = spor_skor_hesapla(metin, ETKINLIK_SPOR_KELIMELERI)
    esik = int(cfg_ayarlar.get("spor_filtre_skor_esigi", 1))
    if spor_skor < esik and cfg_ayarlar.get("etkinlik_sadece_spor", True):
        return bilgi
    bilgi["spor_etkinlik"] = True

    # Tarih arama
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

    # Yer arama
    yer_listesi = cfg_ayarlar.get("yer_kelime_listesi", "amasya,stadyum,spor salonu").split(",")
    for yer in yer_listesi:
        yer = yer.strip().lower()
        if yer and yer in metin_lower:
            bilgi["yer"] = yer.title() if yer != "amasya" else "Amasya"
            break

    # Protokol / Katilimci arama
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
# VERI TOPLAMA MOTORU
# =============================================================================

def rss_oku(kaynak, cfg_ayarlar, timeout=15):
    veriler = []
    try:
        feed = feedparser.parse(kaynak["url"], request_headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        for entry in feed.entries[:10]:
            baslik = metin_temizle(entry.get('title', ''))
            ozet = metin_temizle(entry.get('summary', entry.get('description', '')))
            link = entry.get('link', kaynak["url"])
            tarih_str = entry.get('published', entry.get('updated', ''))
            tarih = tarih_parse(tarih_str)
            icerik = f"{baslik}. {ozet}"

            # Spor filtresi
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
        st.warning(f"RSS hatasi ({kaynak['ad']}): {str(e)[:100]}")
    return veriler

def web_sayfa_oku(kaynak, cfg_ayarlar, timeout=15):
    veriler = []
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        response = requests.get(kaynak["url"], headers=headers, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        seciciler = kaynak.get("secici", ".news-item, .post, article, .haber, .duyuru, .announcement").split(", ")
        bulunan = []
        for secici in seciciler:
            bulunan.extend(soup.select(secici.strip()))
        if not bulunan:
            for link in soup.find_all('a', href=True):
                text = link.get_text(strip=True)
                if len(text) > 20 and len(text) < 200:
                    href = urljoin(kaynak["url"], link['href'])
                    bulunan.append((text, href))
        for item in bulunan[:15]:
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

            # Spor filtresi
            if cfg_ayarlar.get("sadece_spor_icerik", True):
                skor = spor_skor_hesapla(icerik, SPOR_KELIMELERI)
                if skor < int(cfg_ayarlar.get("spor_filtre_skor_esigi", 1)):
                    continue

            tarih = datetime.datetime.now()
            tarih_elem = item.find(['time', 'span', 'div'], class_=re.compile('date|tarih|time'))
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
    except requests.exceptions.Timeout:
        st.warning(f"Zaman asimi ({kaynak['ad']})")
    except requests.exceptions.RequestException as e:
        st.warning(f"Web hatasi ({kaynak['ad']}): {str(e)[:100]}")
    except Exception as e:
        st.warning(f"Genel hata ({kaynak['ad']}): {str(e)[:100]}")
    return veriler

def sosyal_medya_bilgi(kaynak):
    return {
        "id": f"sosyal_{hash(kaynak['url'])}",
        "kaynak_ad": kaynak["ad"],
        "kaynak_url": kaynak["url"],
        "kaynak_tur": "Sosyal Medya",
        "kaynak_kategori": kaynak.get("kategori", "sosyal"),
        "platform": kaynak.get("platform", "bilinmiyor"),
        "grup": kaynak.get("grup", ""),
        "baslik": f"{kaynak['ad']} - Profil Sayfasi",
        "ozet": f"{kaynak.get('grup', '')} grubunun {kaynak.get('platform', '')} sayfasi. Tiklayarak son paylasimlari goruntuleyebilirsiniz.",
        "icerik": "Sosyal medya API erisimi olmadiginda profil sayfalari link olarak sunulur.",
        "link": kaynak["url"],
        "tarih": datetime.datetime.now().isoformat(),
        "tarih_goster": "Profil",
        "zaman_farki": "Surekli",
        "etkinlik": {},
        "durum": "aktif",
        "tip": "profil_linki"
    }

def etkinlik_kaynak_oku(kaynak, cfg_ayarlar, timeout=15):
    return web_sayfa_oku(kaynak, cfg_ayarlar, timeout)

def tum_verileri_topla(config, progress_callback=None):
    tum_veriler = []
    kaynaklar = config["kaynaklar"]
    cfg_ayarlar = config["ayarlar"]
    aktif_rss = [k for k in kaynaklar["rss_kaynaklari"] if k.get("aktif", True)]
    aktif_web = [k for k in kaynaklar["web_siteleri"] if k.get("aktif", True)]
    aktif_sosyal = [k for k in kaynaklar["sosyal_medya"] if k.get("aktif", True)]
    aktif_etkinlik = [k for k in kaynaklar["etkinlik_kaynaklari"] if k.get("aktif", True)]
    toplam_kaynak = len(aktif_rss) + len(aktif_web) + len(aktif_sosyal) + len(aktif_etkinlik)
    mevcut = 0
    for kaynak in aktif_rss:
        mevcut += 1
        if progress_callback:
            progress_callback(mevcut, toplam_kaynak, f"RSS: {kaynak['ad']}")
        veriler = rss_oku(kaynak, cfg_ayarlar)
        tum_veriler.extend(veriler)
        time.sleep(0.5)
    for kaynak in aktif_web:
        mevcut += 1
        if progress_callback:
            progress_callback(mevcut, toplam_kaynak, f"Web: {kaynak['ad']}")
        veriler = web_sayfa_oku(kaynak, cfg_ayarlar)
        tum_veriler.extend(veriler)
        time.sleep(0.5)
    for kaynak in aktif_sosyal:
        mevcut += 1
        if progress_callback:
            progress_callback(mevcut, toplam_kaynak, f"Sosyal: {kaynak['ad']}")
        veri = sosyal_medya_bilgi(kaynak)
        tum_veriler.append(veri)
    for kaynak in aktif_etkinlik:
        mevcut += 1
        if progress_callback:
            progress_callback(mevcut, toplam_kaynak, f"Etkinlik: {kaynak['ad']}")
        veriler = etkinlik_kaynak_oku(kaynak, cfg_ayarlar)
        tum_veriler.extend(veriler)
        time.sleep(0.5)
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
        st.caption(f"v{VERSIYON}")

        st.divider()

        if st.button("🔄 TUM KAYNAKLARI TARA", type="primary", use_container_width=True):
            return "tara"

        if cache_veriler.get("son_tarama"):
            st.info(f"Son tarama: {zaman_farki(cache_veriler['son_tarama'])}")

        st.divider()
        st.subheader("🔍 Filtreler")

        kategoriler = ["Tumu"] + sorted(list(set(v.get("kaynak_kategori", "genel") for v in cache_veriler.get("veriler", []))))
        secili_kategori = st.selectbox("Kategori", kategoriler, key="filtre_kategori")

        turler = ["Tumu", "RSS", "Web", "Sosyal Medya"]
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
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("📊 Toplam Kayit", len(veriler))
    with col2:
        rss_say = len([v for v in veriler if v.get("kaynak_tur") == "RSS"])
        st.metric("📰 RSS Haber", rss_say)
    with col3:
        web_say = len([v for v in veriler if v.get("kaynak_tur") == "Web"])
        st.metric("🌐 Web Haber", web_say)
    with col4:
        sosyal_say = len([v for v in veriler if v.get("kaynak_tur") == "Sosyal Medya"])
        st.metric("📱 Sosyal Medya", sosyal_say)
    with col5:
        etkinlik_say = len([v for v in veriler if v.get("etkinlik", {}).get("tarih")])
        st.metric("📅 Etkinlik", etkinlik_say)
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
        with st.expander(f"{brans['ad']} {'⭐' if brans['oncelik'] == 1 else ''}"):
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
    fmt = config["ayarlar"].get("disa_aktar_format", "excel")
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
    st.info("Tum ayarlari buradan degistirebilirsiniz. Degisiklikler kaydedildikten sonra uygulanir.")

    cfg = config.copy()
    degisiklik = False

    tabs = st.tabs([
        "🎛️ Genel Ayarlar",
        "📰 Kaynak Yonetimi",
        "👥 Taraftar Gruplari",
        "🏆 Spor Branslari",
        "🤖 AI Modulleri",
        "🔍 Filtre & Arama",
        "📊 Gorunum",
        "💾 Yedekleme"
    ])

    # TAB 1: Genel Ayarlar
    with tabs[0]:
        st.subheader("Uygulama Bilgileri")
        cfg["uygulama_adi"] = st.text_input("Uygulama Adi", value=cfg.get("uygulama_adi", "Amasya Spor Radar"))
        cfg["aciklama"] = st.text_area("Aciklama", value=cfg.get("aciklama", ""))

        st.subheader("Tarama Ayarlari")
        a = cfg["ayarlar"]
        a["otomatik_tarama_aktif"] = st.toggle("Otomatik Tarama (Simulasyon)", value=a.get("otomatik_tarama_aktif", False))
        a["otomatik_tarama_araligi_saat"] = st.number_input("Tarama Araligi (Saat)", min_value=1, max_value=24, value=int(a.get("otomatik_tarama_araligi_saat", 6)))
        a["kaynak_zaman_asimi_saniye"] = st.number_input("Kaynak Zaman Asimi (Saniye)", min_value=5, max_value=60, value=int(a.get("kaynak_zaman_asimi_saniye", 15)))
        a["veri_saklama_gun"] = st.number_input("Veri Saklama Suresi (Gun)", min_value=1, max_value=365, value=int(a.get("veri_saklama_gun", 30)))

        st.subheader("Bildirim Ayarlari")
        a["bildirim_aktif"] = st.toggle("Bildirim Aktif", value=a.get("bildirim_aktif", False))
        a["bildirim_kanali"] = st.selectbox("Bildirim Kanali", ["yok", "telegram", "email", "webhook"], index=["yok", "telegram", "email", "webhook"].index(a.get("bildirim_kanali", "yok")))
        a["bildirim_ses"] = st.toggle("Ses Bildirimi", value=a.get("bildirim_ses", False))
        a["bildirim_masaustu"] = st.toggle("Masaustu Bildirimi", value=a.get("bildirim_masaustu", False))

        st.subheader("Dil ve Bolge")
        a["dil"] = st.selectbox("Dil", ["tr", "en"], index=["tr", "en"].index(a.get("dil", "tr")))
        a["zaman_dilimi"] = st.text_input("Zaman Dilimi", value=a.get("zaman_dilimi", "Europe/Istanbul"))
        a["tarih_formati"] = st.text_input("Tarih Format", value=a.get("tarih_formati", "dd.mm.yyyy HH:MM"))

    # TAB 2: Kaynak Yonetimi
    with tabs[1]:
        st.subheader("📡 RSS Kaynaklari")
        for i, kaynak in enumerate(cfg["kaynaklar"]["rss_kaynaklari"]):
            with st.expander(f"{kaynak['ad']} {'✅' if kaynak.get('aktif') else '❌'}"):
                cols = st.columns([3, 3, 2, 1])
                with cols[0]:
                    kaynak["ad"] = st.text_input(f"Ad {i}", value=kaynak["ad"], key=f"rss_ad_{i}")
                with cols[1]:
                    kaynak["url"] = st.text_input(f"URL {i}", value=kaynak["url"], key=f"rss_url_{i}")
                with cols[2]:
                    kaynak["kategori"] = st.text_input(f"Kategori {i}", value=kaynak.get("kategori", "genel"), key=f"rss_kat_{i}")
                with cols[3]:
                    kaynak["aktif"] = st.toggle("Aktif", value=kaynak.get("aktif", True), key=f"rss_aktif_{i}")

        st.subheader("🌐 Web Siteleri")
        for i, kaynak in enumerate(cfg["kaynaklar"]["web_siteleri"]):
            with st.expander(f"{kaynak['ad']} {'✅' if kaynak.get('aktif') else '❌'}"):
                kaynak["ad"] = st.text_input(f"Web Ad {i}", value=kaynak["ad"], key=f"web_ad_{i}")
                kaynak["url"] = st.text_input(f"Web URL {i}", value=kaynak["url"], key=f"web_url_{i}")
                kaynak["secici"] = st.text_input(f"CSS Secici {i}", value=kaynak.get("secici", ""), key=f"web_sec_{i}")
                kaynak["kategori"] = st.text_input(f"Web Kategori {i}", value=kaynak.get("kategori", "genel"), key=f"web_kat_{i}")
                kaynak["aktif"] = st.toggle(f"Web Aktif {i}", value=kaynak.get("aktif", True), key=f"web_aktif_{i}")

        st.subheader("📱 Sosyal Medya")
        for i, kaynak in enumerate(cfg["kaynaklar"]["sosyal_medya"]):
            with st.expander(f"{kaynak['ad']} {'✅' if kaynak.get('aktif') else '❌'}"):
                kaynak["ad"] = st.text_input(f"Sosyal Ad {i}", value=kaynak["ad"], key=f"sos_ad_{i}")
                kaynak["url"] = st.text_input(f"Sosyal URL {i}", value=kaynak["url"], key=f"sos_url_{i}")
                kaynak["platform"] = st.selectbox(f"Platform {i}", ["twitter", "instagram", "facebook", "youtube", "tiktok"], index=["twitter", "instagram", "facebook", "youtube", "tiktok"].index(kaynak.get("platform", "twitter")), key=f"sos_plat_{i}")
                kaynak["grup"] = st.text_input(f"Grup {i}", value=kaynak.get("grup", ""), key=f"sos_grup_{i}")
                kaynak["aktif"] = st.toggle(f"Sosyal Aktif {i}", value=kaynak.get("aktif", True), key=f"sos_aktif_{i}")

        st.subheader("📅 Etkinlik Kaynaklari")
        for i, kaynak in enumerate(cfg["kaynaklar"]["etkinlik_kaynaklari"]):
            with st.expander(f"{kaynak['ad']} {'✅' if kaynak.get('aktif') else '❌'}"):
                kaynak["ad"] = st.text_input(f"Etk Ad {i}", value=kaynak["ad"], key=f"etk_ad_{i}")
                kaynak["url"] = st.text_input(f"Etk URL {i}", value=kaynak["url"], key=f"etk_url_{i}")
                kaynak["kategori"] = st.text_input(f"Etk Kategori {i}", value=kaynak.get("kategori", "etkinlik"), key=f"etk_kat_{i}")
                kaynak["aktif"] = st.toggle(f"Etk Aktif {i}", value=kaynak.get("aktif", True), key=f"etk_aktif_{i}")

        st.divider()
        st.subheader("➕ Yeni Kaynak Ekle")
        yeni_tur = st.selectbox("Kaynak Turu", ["rss", "web", "sosyal", "etkinlik"], key="yeni_tur")
        yeni_ad = st.text_input("Kaynak Adi", key="yeni_ad")
        yeni_url = st.text_input("Kaynak URL", key="yeni_url")
        if st.button("Ekle", key="kaynak_ekle"):
            if yeni_ad and yeni_url:
                yeni = {"ad": yeni_ad, "url": yeni_url, "tur": yeni_tur, "aktif": True, "kategori": "genel"}
                if yeni_tur == "rss":
                    cfg["kaynaklar"]["rss_kaynaklari"].append(yeni)
                elif yeni_tur == "web":
                    yeni["secici"] = ".post, .news-item, article, .haber"
                    cfg["kaynaklar"]["web_siteleri"].append(yeni)
                elif yeni_tur == "sosyal":
                    yeni["platform"] = "twitter"
                    yeni["grup"] = ""
                    cfg["kaynaklar"]["sosyal_medya"].append(yeni)
                else:
                    cfg["kaynaklar"]["etkinlik_kaynaklari"].append(yeni)
                st.success(f"{yeni_ad} eklendi!")
                degisiklik = True

    # TAB 3: Taraftar Gruplari
    with tabs[2]:
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
        yeni_tg_takim = st.text_input("Bagli Takim", key="yeni_tg_takim")
        if st.button("Grup Ekle", key="tg_ekle"):
            if yeni_tg_ad and yeni_tg_kisa:
                cfg["taraftar_gruplari"].append({
                    "ad": yeni_tg_ad, "kisa_ad": yeni_tg_kisa, "renkler": ["Yesil", "Siyah"],
                    "takim": yeni_tg_takim or "Amasyaspor FK",
                    "platformlar": {"twitter": yeni_tg_kisa, "instagram": yeni_tg_kisa, "facebook": yeni_tg_kisa},
                    "aktif": True, "oncelik": 2
                })
                st.success(f"{yeni_tg_ad} eklendi!")
                degisiklik = True

    # TAB 4: Spor Branslari
    with tabs[3]:
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
        yeni_br_fed = st.text_input("Federasyon", key="yeni_br_fed")
        if st.button("Brans Ekle", key="br_ekle"):
            if yeni_br_ad and yeni_br_kisa:
                cfg["spor_branslari"].append({
                    "ad": yeni_br_ad, "kisa_ad": yeni_br_kisa, "takimlar": [f"Amasya {yeni_br_ad}"],
                    "federasyon": yeni_br_fed or "TFF", "oncelik": 2, "amasya_basarilari": ""
                })
                st.success(f"{yeni_br_ad} eklendi!")
                degisiklik = True

    # TAB 5: AI Modulleri
    with tabs[4]:
        st.subheader("🤖 Yapay Zeka Modulleri")
        a = cfg["ayarlar"]
        a["ai_modul_aktif"] = st.toggle("AI Modulunu Aktif Et", value=a.get("ai_modul_aktif", False))
        st.info("AI modulu icerik ozetleme, duygu analizi ve etkinlik tanima yapar. Tamamen yerel calisir, dis API kullanmaz.")

        for modul_adi, modul in cfg["ai_modulleri"].items():
            with st.expander(f"{modul_adi.capitalize()}"):
                modul["aktif"] = st.toggle(f"{modul_adi} Aktif", value=modul.get("aktif", False), key=f"ai_{modul_adi}")
                modul["aciklama"] = st.text_area(f"Aciklama", value=modul.get("aciklama", ""), key=f"ai_acik_{modul_adi}")
                if modul_adi == "ozetleyici":
                    modul["parametreler"]["max_cumle"] = st.number_input("Max Cumle", min_value=1, max_value=10, value=int(modul["parametreler"].get("max_cumle", 3)), key=f"ai_max_{modul_adi}")
                    modul["parametreler"]["min_cumle"] = st.number_input("Min Cumle", min_value=1, max_value=5, value=int(modul["parametreler"].get("min_cumle", 1)), key=f"ai_min_{modul_adi}")

    # TAB 6: Filtre & Arama
    with tabs[5]:
        st.subheader("🔍 Icerik Filtreleme")
        a = cfg["ayarlar"]
        a["sadece_spor_icerik"] = st.toggle("Sadece Spor Icerigi Goster", value=a.get("sadece_spor_icerik", True), help="Sporla alakasi olmayan haberleri filtreler")
        a["spor_filtre_skor_esigi"] = st.number_input("Spor Filtre Skor Esigi (Kac spor kelimesi gecmeli)", min_value=0, max_value=10, value=int(a.get("spor_filtre_skor_esigi", 1)), help="Daha yuksek deger = daha katı filtre")
        a["etkinlik_sadece_spor"] = st.toggle("Etkinlikler Sadece Spor Olsun", value=a.get("etkinlik_sadece_spor", True), help="Sporla alakasi olmayan etkinlikleri gosterme")

        st.subheader("📝 Anahtar Kelimeler")
        cfg["anahtar_kelimeler"] = st.text_area("Anahtar Kelimeler (virgulle ayir)", value=", ".join(cfg.get("anahtar_kelimeler", [])), height=100).split(", ")
        cfg["etiketler"] = st.text_area("Sosyal Medya Etiketleri (virgulle ayir)", value=", ".join(cfg.get("etiketler", [])), height=80).split(", ")

        st.subheader("🏛️ Protokol ve Yer Kelimeleri")
        a["protokol_kelime_listesi"] = st.text_area("Protokol Kelimeleri (virgulle)", value=a.get("protokol_kelime_listesi", "vali,belediye baskani"), height=60)
        a["yer_kelime_listesi"] = st.text_area("Yer Kelimeleri (virgulle)", value=a.get("yer_kelime_listesi", "amasya,stadyum"), height=60)

        st.subheader("😊 Duygu Analizi Kelimeleri")
        a["olumlu_duygu_kelimeleri"] = st.text_area("Olumlu Kelimeler (virgulle)", value=a.get("olumlu_duygu_kelimeleri", "basari,zafer"), height=60)
        a["olumsuz_duygu_kelimeleri"] = st.text_area("Olumsuz Kelimeler (virgulle)", value=a.get("olumsuz_duygu_kelimeleri", "maglup,kaybetti"), height=60)

    # TAB 7: Gorunum
    with tabs[6]:
        st.subheader("🎨 Görünüm Ayarlari")
        a = cfg["ayarlar"]
        a["sayfa_basligi"] = st.text_input("Sayfa Basligi", value=a.get("sayfa_basligi", "Amasya Spor Radar"))
        a["favicon"] = st.selectbox("Favicon", ["futbol", "trophy", "fire", "star", "zap"], index=["futbol", "trophy", "fire", "star", "zap"].index(a.get("favicon", "futbol")))
        a["gorunum_tema"] = st.selectbox("Tema", ["acik", "koyu", "otomatik"], index=["acik", "koyu", "otomatik"].index(a.get("gorunum_tema", "acik")))
        a["sayfa_basina_kayit"] = st.number_input("Sayfa Basina Kayit", min_value=5, max_value=100, value=int(a.get("sayfa_basina_kayit", 20)))
        a["varsayilan_siralama"] = st.selectbox("Varsayilan Siralama", ["tarih_yeni", "tarih_eski", "alfabetik"], index=["tarih_yeni", "tarih_eski", "alfabetik"].index(a.get("varsayilan_siralama", "tarih_yeni")))

        st.subheader("🔖 Rozet Ayarlari")
        a["kaynak_rozetleri_goster"] = st.toggle("Kaynak Rozetleri", value=a.get("kaynak_rozetleri_goster", True))
        a["duygu_rozetleri_goster"] = st.toggle("Duygu Rozetleri", value=a.get("duygu_rozetleri_goster", True))
        a["brans_rozetleri_goster"] = st.toggle("Brans Rozetleri", value=a.get("brans_rozetleri_goster", True))
        a["grup_rozetleri_goster"] = st.toggle("Grup Rozetleri", value=a.get("grup_rozetleri_goster", True))
        a["etkinlik_karti_goster"] = st.toggle("Etkinlik Karti Goster", value=a.get("etkinlik_karti_goster", True))
        a["protokol_vurgula"] = st.toggle("Protokol Vurgula", value=a.get("protokol_vurgula", True))
        a["taraftar_vurgula"] = st.toggle("Taraftar Vurgula", value=a.get("taraftar_vurgula", True))

        st.subheader("🎨 Özel CSS")
        a["ozellestirilmis_css"] = st.text_area("Özel CSS Kodu", value=a.get("ozellestirilmis_css", ""), height=100)

        st.subheader("💾 Disa Aktar")
        a["disa_aktar_format"] = st.selectbox("Varsayilan Format", ["excel", "csv"], index=["excel", "csv"].index(a.get("disa_aktar_format", "excel")))

    # TAB 8: Yedekleme
    with tabs[7]:
        st.subheader("💾 Config Yedekleme")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(config_indir(cfg), unsafe_allow_html=True)
            st.caption("Mevcut ayarlari config.json olarak indir")
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
            st.success("Varsayilan ayarlara donuldu! Sayfa yenileniyor...")
            st.rerun()

        st.subheader("🐛 Debug")
        a["debug_modu"] = st.toggle("Debug Modu", value=a.get("debug_modu", False))
        if a.get("debug_modu"):
            st.json(cfg)

    # Kaydet butonu
    st.divider()
    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("💾 TUM AYARLARI KAYDET", type="primary", use_container_width=True):
            if config_yaz(cfg):
                st.success("✅ Ayarlar kaydedildi! Degisiklikler bir sonraki taramada aktif olacak.")
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

def tarama_ekrani(config):
    st.title("🔄 Kaynaklar Taraniyor...")
    progress_bar = st.progress(0)
    durum_text = st.empty()

    def progress_callback(mevcut, toplam, mesaj):
        progress = int((mevcut / toplam) * 100)
        progress_bar.progress(progress)
        durum_text.text(f"{mevcut}/{toplam} - {mesaj}")

    yeni_veriler = tum_verileri_topla(config, progress_callback)
    durum_text.text("Veriler isleniyor...")
    yeni_veriler = verileri_isle(yeni_veriler, config)

    cache = cache_oku()
    saklama = int(config["ayarlar"].get("veri_saklama_gun", 30))
    cache = verileri_birlestir(yeni_veriler, cache, saklama)
    cache_yaz(cache)

    progress_bar.empty()
    durum_text.empty()

    st.success(f"Tarama tamamlandi! {cache['istatistikler']['son_eklenen']} yeni kayit bulundu.")
    st.info(f"Toplam kayit sayisi: {cache['istatistikler']['toplam_kayit']}")
    time.sleep(2)
    st.rerun()

def ana_ekran(config, cache):
    st.title(f"⚽ {config.get('uygulama_adi', 'Amasya Spor Radar')}")
    st.caption(config.get('aciklama', 'Amasya sportif istihbarat sistemi'))

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
            st.info("Henuz veri yok. Lutfen soldaki menuden 'TUM KAYNAKLARI TARA' butonuna basin.")
            st.markdown("""
            ### Baslangic
            1. Soldaki sidebar'dan **"TUM KAYNAKLARI TARA"** butonuna basin
            2. Sistem kaynaklari tarayacak
            3. Sonuclar burada listelenecek
            4. Filtrelerle aradiginizi bulun
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
            st.info("Henuz istatistik icin yeterli veri yok.")

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
        tarama_ekrani(config)
        return

    ana_ekran(config, cache)

if __name__ == "__main__":
    main()
