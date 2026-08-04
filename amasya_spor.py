#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Amasya Spor Radar v1.0
Amasya'daki tüm sportif faaliyetleri, haberleri, etkinlikleri ve taraftar oluşumlarını takip eden istihbarat sistemi.
Tek dosya, tek komutla çalışır.
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
from dateutil.tz import tzlocal
from urllib.parse import urljoin, urlparse
import pandas as pd
from collections import defaultdict
import html

# =============================================================================
# KONFIGÜRASYON VE SABİTLER
# =============================================================================

CONFIG_DOSYA = "config.json"
CACHE_DOSYA = "cache.json"
LOGO_EMOJI = "⚽"
VERSIYON = "1.0"

# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

@st.cache_data(ttl=300)
def config_oku():
    """Config dosyasını okur, yoksa varsayılan oluşturur."""
    try:
        with open(CONFIG_DOSYA, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        st.error("❌ config.json bulunamadı! Lütfen config.json dosyasını aynı klasöre koyun.")
        return None

def cache_oku():
    """Önbellek dosyasını okur."""
    if os.path.exists(CACHE_DOSYA):
        try:
            with open(CACHE_DOSYA, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"veriler": [], "son_tarama": None, "istatistikler": {}}
    return {"veriler": [], "son_tarama": None, "istatistikler": {}}

def cache_yaz(veri):
    """Önbellek dosyasına yazar."""
    try:
        with open(CACHE_DOSYA, 'w', encoding='utf-8') as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Cache yazma hatası: {e}")

def metin_temizle(text):
    """HTML etiketlerini ve özel karakterleri temizler."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def tarih_parse(tarih_str):
    """Çeşitli tarih formatlarını parse eder."""
    if not tarih_str:
        return datetime.datetime.now()
    try:
        # RSS standart formatları
        return date_parser.parse(tarih_str)
    except:
        pass

    # Türkçe tarih formatları
    aylar = {
        'ocak': 1, 'şubat': 2, 'subat': 2, 'mart': 3, 'nisan': 4,
        'mayıs': 5, 'mayis': 5, 'haziran': 6, 'temmuz': 7, 'ağustos': 8,
        'agustos': 8, 'eylül': 9, 'eylul': 9, 'ekim': 10, 'kasım': 11,
        'kasim': 11, 'aralık': 12, 'aralik': 12
    }

    # "5 Ocak 2024" formatı
    pattern = r'(\d{1,2})\s+([a-zA-ZçÇğĞıİöÖşŞüÜ]+)\s+(\d{4})'
    match = re.search(pattern, tarih_str.lower())
    if match:
        gun, ay_str, yil = match.groups()
        ay = aylar.get(ay_str, 1)
        return datetime.datetime(int(yil), ay, int(gun))

    # "05.01.2024" veya "05/01/2024" formatı
    pattern = r'(\d{1,2})[./](\d{1,2})[./](\d{4})'
    match = re.search(pattern, tarih_str)
    if match:
        gun, ay, yil = map(int, match.groups())
        return datetime.datetime(yil, ay, gun)

    return datetime.datetime.now()

def kisa_tarih(dt):
    """Tarihi kısa formata çevirir."""
    if isinstance(dt, str):
        dt = tarih_parse(dt)
    return dt.strftime("%d.%m.%Y %H:%M")

def zaman_farki(dt):
    """Şu an ile verilen tarih arasındaki farkı insan okunabilir formatta döndürür."""
    if isinstance(dt, str):
        dt = tarih_parse(dt)
    simdi = datetime.datetime.now(dt.tzinfo) if dt.tzinfo else datetime.datetime.now()
    fark = simdi - dt
    if fark.days > 0:
        return f"{fark.days} gün önce"
    saat = fark.seconds // 3600
    if saat > 0:
        return f"{saat} saat önce"
    dakika = fark.seconds // 60
    if dakika > 0:
        return f"{dakika} dakika önce"
    return "Az önce"

def basit_ozetle(metin, cumle_sayisi=3):
    """Basit özetleme: İlk N cümleyi alır."""
    if not metin:
        return ""
    cumleler = re.split(r'(?<=[.!?])\s+', metin)
    cumleler = [c for c in cumleler if len(c.strip()) > 10]
    if len(cumleler) <= cumle_sayisi:
        return metin
    return " ".join(cumleler[:cumle_sayisi]) + "..."

def etkinlik_bilgisi_cikar(metin):
    """Metin içinden etkinlik bilgilerini çıkarır (tarih, yer, katılımcılar)."""
    bilgi = {"tarih": None, "yer": None, "katilimci": None, "protokol": False}

    if not metin:
        return bilgi

    metin_lower = metin.lower()

    # Tarih arama
    tarih_patternler = [
        r'(\d{1,2})\s+(ocak|şubat|subat|mart|nisan|mayıs|mayis|haziran|temmuz|ağustos|agustos|eylül|eylul|ekim|kasım|kasim|aralık|aralik)\s+(\d{4})',
        r'(\d{1,2})[./](\d{1,2})[./](\d{4})',
        r'(\d{1,2})[./](\d{1,2})[./](\d{2})',
    ]
    for pattern in tarih_patternler:
        match = re.search(pattern, metin_lower)
        if match:
            bilgi["tarih"] = match.group(0)
            break

    # Yer arama
    yer_kelimeleri = [
        "amasya", "12 haziran stadyumu", "spor salonu", "spor kompleksi",
        "yüzme havuzu", "stad", "salon", "tenis kortu", "atletizm pisti",
        "merzifon", "suluova", "taşova", "gümüşhacıköy"
    ]
    for yer in yer_kelimeleri:
        if yer in metin_lower:
            # Cümle içinde yer geçiyorsa al
            cumleler = re.split(r'(?<=[.!?])\s+', metin_lower)
            for cumle in cumleler:
                if yer in cumle:
                    bilgi["yer"] = yer.title() if yer != "amasya" else "Amasya"
                    break
            if bilgi["yer"]:
                break

    # Katılımcı / Protokol arama
    protokol_kelimeleri = [
        "vali", "belediye başkanı", "milletvekili", "kaymakam", "protokol",
        "gençlik ve spor il müdürü", "gsb müdürü", "rektör", "dekan",
        "spor il müdürü", "bakan", "başkan", "müdür"
    ]
    katilimcilar = []
    for kelime in protokol_kelimeleri:
        if kelime in metin_lower:
            katilimcilar.append(kelime.title())
            bilgi["protokol"] = True

    if katilimcilar:
        bilgi["katilimci"] = ", ".join(katilimcilar[:3])

    return bilgi

def spor_bransi_tespit(metin, branslar):
    """Metinde geçen spor branşlarını tespit eder."""
    bulunan = []
    if not metin:
        return bulunan
    metin_lower = metin.lower()
    for brans in branslar:
        if brans["kisa_ad"] in metin_lower or brans["ad"].lower() in metin_lower:
            bulunan.append(brans)
    return bulunan

def taraftar_grubu_tespit(metin, gruplar):
    """Metinde geçen taraftar gruplarını tespit eder."""
    bulunan = []
    if not metin:
        return bulunan
    metin_lower = metin.lower()
    for grup in gruplar:
        if grup["kisa_ad"] in metin_lower or grup["ad"].lower() in metin_lower:
            bulunan.append(grup)
    return bulunan

def duygu_analizi_basit(metin):
    """Basit duygu analizi: Olumlu/olumsuz/nötr."""
    if not metin:
        return "nötr"
    metin_lower = metin.lower()

    olumlu = ["başarı", "zafer", "şampiyon", "kazandı", "güzel", "harika", "tebrik", "bravo", "muhteşem", "gurur", "mutlu", "sevinç"]
    olumsuz = ["mağlup", "kaybetti", "başarısız", "kötü", "berbat", "protesto", "eylem", "kavga", "şikayet", "sorun", "hüsran", "üzücü"]

    olumlu_say = sum(1 for k in olumlu if k in metin_lower)
    olumsuz_say = sum(1 for k in olumsuz if k in metin_lower)

    if olumlu_say > olumsuz_say:
        return "olumlu"
    elif olumsuz_say > olumlu_say:
        return "olumsuz"
    return "nötr"

# =============================================================================
# VERİ TOPLAMA MOTORU
# =============================================================================

def rss_oku(kaynak, timeout=15):
    """RSS kaynağından veri okur."""
    veriler = []
    try:
        feed = feedparser.parse(kaynak["url"], request_headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        for entry in feed.entries[:10]:  # Son 10 kayıt
            baslik = metin_temizle(entry.get('title', ''))
            ozet = metin_temizle(entry.get('summary', entry.get('description', '')))
            link = entry.get('link', kaynak["url"])
            tarih_str = entry.get('published', entry.get('updated', ''))
            tarih = tarih_parse(tarih_str)

            icerik = f"{baslik}. {ozet}"

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
                "etkinlik": etkinlik_bilgisi_cikar(icerik),
                "durum": "aktif"
            }
            veriler.append(veri)

    except Exception as e:
        st.warning(f"⚠️ RSS hatası ({kaynak['ad']}): {str(e)[:100]}")

    return veriler

def web_sayfa_oku(kaynak, timeout=15):
    """Web sayfasından haber/duyuru okur."""
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

        # Farklı seçicileri dene
        seciciler = kaynak.get("secici", ".news-item, .post, article, .haber, .duyuru, .announcement").split(", ")

        bulunan = []
        for secici in seciciler:
            bulunan.extend(soup.select(secici.strip()))

        # Hiçbir şey bulunamazsa tüm linkleri dene
        if not bulunan:
            for link in soup.find_all('a', href=True):
                text = link.get_text(strip=True)
                if len(text) > 20 and len(text) < 200:
                    href = urljoin(kaynak["url"], link['href'])
                    bulunan.append((text, href))

        # Sonuçları işle
        for item in bulunan[:15]:
            if isinstance(item, tuple):
                baslik, link = item
                ozet = ""
            else:
                baslik = metin_temizle(item.get_text(separator=' ', strip=True)[:150])
                link_elem = item.find('a') or item.find_parent('a')
                link = urljoin(kaynak["url"], link_elem['href']) if link_elem and link_elem.get('href') else kaynak["url"]
                # Tüm metni al
                ozet = metin_temizle(item.get_text(separator=' ', strip=True))

            if not baslik or len(baslik) < 10:
                continue

            # Tarih bulmaya çalış
            tarih = datetime.datetime.now()
            # Meta veya element içinde tarih ara
            tarih_elem = item.find(['time', 'span', 'div'], class_=re.compile('date|tarih|time'))
            if tarih_elem:
                tarih = tarih_parse(tarih_elem.get_text())

            icerik = f"{baslik}. {ozet}"

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
                "etkinlik": etkinlik_bilgisi_cikar(icerik),
                "durum": "aktif"
            }
            veriler.append(veri)

    except requests.exceptions.Timeout:
        st.warning(f"⏱️ Zaman aşımı ({kaynak['ad']})")
    except requests.exceptions.RequestException as e:
        st.warning(f"⚠️ Web hatası ({kaynak['ad']}): {str(e)[:100]}")
    except Exception as e:
        st.warning(f"⚠️ Genel hata ({kaynak['ad']}): {str(e)[:100]}")

    return veriler

def sosyal_medya_bilgi(kaynak):
    """Sosyal medya kaynağı için bilgi kartı oluşturur (API olmadan link ve açıklama)."""
    return {
        "id": f"sosyal_{hash(kaynak['url'])}",
        "kaynak_ad": kaynak["ad"],
        "kaynak_url": kaynak["url"],
        "kaynak_tur": "Sosyal Medya",
        "kaynak_kategori": kaynak.get("kategori", "sosyal"),
        "platform": kaynak.get("platform", "bilinmiyor"),
        "grup": kaynak.get("grup", ""),
        "baslik": f"{kaynak['ad']} - Profil Sayfası",
        "ozet": f"{kaynak.get('grup', '')} grubunun {kaynak.get('platform', '')} sayfası. Tıklayarak son paylaşımları görüntüleyebilirsiniz.",
        "icerik": "Sosyal medya API erişimi olmadığında profil sayfaları link olarak sunulur. Gelecekte API entegrasyonu eklenebilir.",
        "link": kaynak["url"],
        "tarih": datetime.datetime.now().isoformat(),
        "tarih_goster": "Profil",
        "zaman_farki": "Sürekli",
        "etkinlik": {},
        "durum": "aktif",
        "tip": "profil_linki"
    }

def etkinlik_kaynak_oku(kaynak, timeout=15):
    """Etkinlik kaynaklarından veri okur (web scraping)."""
    # Web sayfası okuma ile aynı mantık
    return web_sayfa_oku(kaynak, timeout)

def tum_verileri_topla(config, progress_callback=None):
    """Tüm aktif kaynaklardan veri toplar."""
    tum_veriler = []
    kaynaklar = config["kaynaklar"]

    aktif_rss = [k for k in kaynaklar["rss_kaynaklari"] if k.get("aktif", True)]
    aktif_web = [k for k in kaynaklar["web_siteleri"] if k.get("aktif", True)]
    aktif_sosyal = [k for k in kaynaklar["sosyal_medya"] if k.get("aktif", True)]
    aktif_etkinlik = [k for k in kaynaklar["etkinlik_kaynaklari"] if k.get("aktif", True)]

    toplam_kaynak = len(aktif_rss) + len(aktif_web) + len(aktif_sosyal) + len(aktif_etkinlik)
    mevcut = 0

    # RSS kaynakları
    for kaynak in aktif_rss:
        mevcut += 1
        if progress_callback:
            progress_callback(mevcut, toplam_kaynak, f"📰 {kaynak['ad']}")
        veriler = rss_oku(kaynak)
        tum_veriler.extend(veriler)
        time.sleep(0.5)  # Sunucuları yormamak için bekle

    # Web siteleri
    for kaynak in aktif_web:
        mevcut += 1
        if progress_callback:
            progress_callback(mevcut, toplam_kaynak, f"🌐 {kaynak['ad']}")
        veriler = web_sayfa_oku(kaynak)
        tum_veriler.extend(veriler)
        time.sleep(0.5)

    # Sosyal medya (profil linkleri)
    for kaynak in aktif_sosyal:
        mevcut += 1
        if progress_callback:
            progress_callback(mevcut, toplam_kaynak, f"📱 {kaynak['ad']}")
        veri = sosyal_medya_bilgi(kaynak)
        tum_veriler.append(veri)

    # Etkinlik kaynakları
    for kaynak in aktif_etkinlik:
        mevcut += 1
        if progress_callback:
            progress_callback(mevcut, toplam_kaynak, f"📅 {kaynak['ad']}")
        veriler = etkinlik_kaynak_oku(kaynak)
        tum_veriler.extend(veriler)
        time.sleep(0.5)

    return tum_veriler

def verileri_isle(veriler, config):
    """Toplanan verileri işler: branş, taraftar, duygu analizi, özetleme."""
    branslar = config["spor_branslari"]
    gruplar = config["taraftar_gruplari"]
    ai_aktif = config["ayarlar"].get("ai_modul_aktif", False)

    for veri in veriler:
        icerik = veri.get("icerik", "")

        # Spor branşı tespiti
        veri["spor_branslari"] = spor_bransi_tespit(icerik, branslar)

        # Taraftar grubu tespiti
        veri["taraftar_gruplari"] = taraftar_grubu_tespit(icerik, gruplar)

        # Duygu analizi
        veri["duygu"] = duygu_analizi_basit(icerik)

        # AI Özetleme
        if ai_aktif and icerik and len(icerik) > 100:
            veri["ai_ozet"] = basit_ozetle(icerik, 3)
        else:
            veri["ai_ozet"] = veri.get("ozet", "")

    return veriler

def verileri_birlestir(yeni_veriler, cache):
    """Yeni verileri cache ile birleştirir, tekrarları kaldırır."""
    mevcut_ids = {v["id"] for v in cache.get("veriler", [])}
    eklenen = 0

    for veri in yeni_veriler:
        if veri["id"] not in mevcut_ids:
            cache["veriler"].append(veri)
            mevcut_ids.add(veri["id"])
            eklenen += 1

    # Tarihe göre sırala (yeniden eskiye)
    cache["veriler"].sort(key=lambda x: x.get("tarih", ""), reverse=True)

    # Eski verileri temizle (ayarlanan gün sayısınca)
    saklama_gun = config_oku()["ayarlar"].get("veri_saklama_gun", 30)
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
# STREAMLIT ARAYÜZÜ
# =============================================================================

def sayfa_yapilandir():
    """Streamlit sayfa yapılandırması."""
    st.set_page_config(
        page_title="Amasya Spor Radar",
        page_icon="⚽",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def sidebar_filtreler(config, cache_veriler):
    """Sidebar filtrelerini oluşturur."""
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Amasya_Merkez.png/250px-Amasya_Merkez.png", width=150)
        st.title("⚽ Amasya Spor Radar")
        st.caption(f"v{VERSIYON} | Amasya Sportif İstihbarat Sistemi")

        st.divider()

        # Tarama butonu
        if st.button("🔄 TÜM KAYNAKLARI TARA", type="primary", use_container_width=True):
            return "tara"

        # Son tarama bilgisi
        if cache_veriler.get("son_tarama"):
            st.info(f"🕐 Son tarama: {zaman_farki(cache_veriler['son_tarama'])}")

        st.divider()

        # Filtreler
        st.subheader("🔍 Filtreler")

        # Kategori filtresi
        kategoriler = ["Tümü"] + sorted(list(set(v.get("kaynak_kategori", "genel") for v in cache_veriler.get("veriler", []))))
        secili_kategori = st.selectbox("Kategori", kategoriler, key="filtre_kategori")

        # Kaynak türü filtresi
        turler = ["Tümü", "RSS", "Web", "Sosyal Medya"]
        secili_tur = st.selectbox("Kaynak Türü", turler, key="filtre_tur")

        # Spor branşı filtresi
        branslar_liste = ["Tümü"] + [b["ad"] for b in config["spor_branslari"]]
        secili_brans = st.selectbox("Spor Branşı", branslar_liste, key="filtre_brans")

        # Taraftar grubu filtresi
        gruplar_liste = ["Tümü"] + [g["ad"] for g in config["taraftar_gruplari"]]
        secili_grup = st.selectbox("Taraftar Grubu", gruplar_liste, key="filtre_grup")

        # Duygu filtresi
        duygular = ["Tümü", "olumlu", "olumsuz", "nötr"]
        secili_duygu = st.selectbox("Duygu Durumu", duygular, key="filtre_duygu")

        # Tarih aralığı
        st.subheader("📅 Tarih Aralığı")
        tarih_secenekleri = ["Tümü", "Son 24 Saat", "Son 3 Gün", "Son 7 Gün", "Son 30 Gün"]
        secili_tarih = st.selectbox("Zaman", tarih_secenekleri, key="filtre_tarih")

        # Arama
        st.subheader("🔎 Arama")
        arama_kelimesi = st.text_input("Kelime ara...", key="arama")

        st.divider()

        # Ayarlar
        with st.expander("⚙️ Gelişmiş Ayarlar"):
            ai_modul = st.toggle("AI Özetleme Modülü", value=config["ayarlar"].get("ai_modul_aktif", False))
            if ai_modul != config["ayarlar"].get("ai_modul_aktif", False):
                config["ayarlar"]["ai_modul_aktif"] = ai_modul
                # Config'i kaydet
                try:
                    with open(CONFIG_DOSYA, 'w', encoding='utf-8') as f:
                        json.dump(config, f, ensure_ascii=False, indent=2)
                    st.success("Ayar kaydedildi!")
                except:
                    pass

            st.caption("🤖 AI Modülü: Haberleri otomatik özetler ve etkinlik bilgilerini çıkarır.")

            otomatik = st.toggle("Otomatik Tarama (Gelecek Özellik)", value=False, disabled=True)
            st.caption("🔔 Otomatik tarama ve bildirim özelliği yakında eklenecek.")

            if st.button("🗑️ Önbelleği Temizle"):
                if os.path.exists(CACHE_DOSYA):
                    os.remove(CACHE_DOSYA)
                st.success("Önbellek temizlendi!")
                st.rerun()

        # Hakkında
        with st.expander("ℹ️ Hakkında"):
            st.markdown("""
            **Amasya Spor Radar** v1.0

            Amasya'daki tüm sportif faaliyetleri, haberleri, etkinlikleri ve taraftar oluşumlarını takip eden istihbarat sistemi.

            **Özellikler:**
            - 38+ online kaynak
            - RSS ve Web scraping
            - Taraftar grup takibi
            - Spor branşı analizi
            - Etkinlik tanıma
            - Duygu analizi
            - AI özetleme (opsiyonel)

            **Geliştirilebilir:**
            - config.json dosyasını düzenleyerek yeni kaynaklar ekleyebilirsiniz.
            - AI modülünü açıp kapatabilirsiniz.
            - Otomatik tarama ve bildirim (yakında).
            """)

        st.divider()
        st.caption("Made with ❤️ for Amasya")

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
    """Verileri filtreler."""
    if not veriler:
        return []

    filtrelenmis = veriler.copy()

    # Kategori filtresi
    if filtreler["kategori"] != "Tümü":
        filtrelenmis = [v for v in filtrelenmis if v.get("kaynak_kategori") == filtreler["kategori"]]

    # Tür filtresi
    if filtreler["tur"] != "Tümü":
        filtrelenmis = [v for v in filtrelenmis if v.get("kaynak_tur") == filtreler["tur"]]

    # Branş filtresi
    if filtreler["brans"] != "Tümü":
        filtrelenmis = [v for v in filtrelenmis if any(b["ad"] == filtreler["brans"] for b in v.get("spor_branslari", []))]

    # Grup filtresi
    if filtreler["grup"] != "Tümü":
        filtrelenmis = [v for v in filtrelenmis if any(g["ad"] == filtreler["grup"] for g in v.get("taraftar_gruplari", []))]

    # Duygu filtresi
    if filtreler["duygu"] != "Tümü":
        filtrelenmis = [v for v in filtrelenmis if v.get("duygu") == filtreler["duygu"]]

    # Tarih filtresi
    if filtreler["tarih"] != "Tümü":
        simdi = datetime.datetime.now()
        if filtreler["tarih"] == "Son 24 Saat":
            sinir = simdi - datetime.timedelta(hours=24)
        elif filtreler["tarih"] == "Son 3 Gün":
            sinir = simdi - datetime.timedelta(days=3)
        elif filtreler["tarih"] == "Son 7 Gün":
            sinir = simdi - datetime.timedelta(days=7)
        elif filtreler["tarih"] == "Son 30 Gün":
            sinir = simdi - datetime.timedelta(days=30)
        else:
            sinir = simdi - datetime.timedelta(days=9999)

        filtrelenmis = [v for v in filtrelenmis if tarih_parse(v.get("tarih", simdi.isoformat())) > sinir]

    # Arama filtresi
    if filtreler["arama"]:
        arama = filtreler["arama"].lower()
        filtrelenmis = [v for v in filtrelenmis if arama in v.get("baslik", "").lower() or arama in v.get("ozet", "").lower() or arama in v.get("icerik", "").lower()]

    return filtrelenmis

def haber_karti_goster(veri, config):
    """Tek bir haber/veri kartı gösterir."""
    # Duygu rengi
    duygu = veri.get("duygu", "nötr")
    duygu_renk = {"olumlu": "🟢", "olumsuz": "🔴", "nötr": "⚪"}.get(duygu, "⚪")

    # Etkinlik badge'leri
    etkinlik = veri.get("etkinlik", {})
    etkinlik_badges = []
    if etkinlik.get("tarih"):
        etkinlik_badges.append(f"📅 {etkinlik['tarih']}")
    if etkinlik.get("yer"):
        etkinlik_badges.append(f"📍 {etkinlik['yer']}")
    if etkinlik.get("protokol"):
        etkinlik_badges.append("🏛️ Protokol Katılımı")
    if etkinlik.get("katilimci"):
        etkinlik_badges.append(f"👤 {etkinlik['katilimci']}")

    # Branş badge'leri
    brans_badges = []
    for brans in veri.get("spor_branslari", [])[:3]:
        brans_badges.append(f"🏆 {brans['ad']}")

    # Grup badge'leri
    grup_badges = []
    for grup in veri.get("taraftar_gruplari", [])[:3]:
        grup_badges.append(f"👥 {grup['ad']}")

    # Kart içeriği
    with st.container():
        col1, col2 = st.columns([4, 1])

        with col1:
            # Başlık ve link
            st.markdown(f"### [{veri.get('baslik', 'Başlık Yok')}]({veri.get('link', '#')})")

            # Özet
            ozet = veri.get("ai_ozet") or veri.get("ozet", "")
            if ozet:
                st.markdown(f"{ozet[:250]}{'...' if len(ozet) > 250 else ''}")

            # Badge'ler
            badges = []
            badges.append(f"📰 {veri.get('kaynak_ad', 'Bilinmiyor')}")
            badges.append(f"🏷️ {veri.get('kaynak_tur', 'Genel')}")
            badges.append(f"🕐 {veri.get('zaman_farki', 'Bilinmiyor')}")
            badges.append(duygu_renk)

            if etkinlik_badges:
                badges.extend(etkinlik_badges)
            if brans_badges:
                badges.extend(brans_badges)
            if grup_badges:
                badges.extend(grup_badges)

            st.markdown(" | ".join(badges))

        with col2:
            # Kaynağa git butonu
            st.link_button("🔗 Kaynağa Git", veri.get("link", "#"), use_container_width=True)

            # Detaylar
            with st.expander("📋 Detaylar"):
                st.write(f"**Kaynak:** {veri.get('kaynak_ad', 'Bilinmiyor')}")
                st.write(f"**Tür:** {veri.get('kaynak_tur', 'Bilinmiyor')}")
                st.write(f"**Kategori:** {veri.get('kaynak_kategori', 'Genel')}")
                st.write(f"**Yayın Tarihi:** {veri.get('tarih_goster', 'Bilinmiyor')}")
                st.write(f"**Duygu:** {duygu}")

                if veri.get("spor_branslari"):
                    st.write(f"**Spor Branşları:** {', '.join(b['ad'] for b in veri['spor_branslari'])}")

                if veri.get("taraftar_gruplari"):
                    st.write(f"**Taraftar Grupları:** {', '.join(g['ad'] for g in veri['taraftar_gruplari'])}")

                if etkinlik.get("tarih"):
                    st.write(f"**Etkinlik Tarihi:** {etkinlik['tarih']}")
                if etkinlik.get("yer"):
                    st.write(f"**Etkinlik Yeri:** {etkinlik['yer']}")
                if etkinlik.get("katilimci"):
                    st.write(f"**Katılımcılar:** {etkinlik['katilimci']}")

        st.divider()

def istatistik_paneli(veriler, config):
    """Üst istatistik panelini gösterir."""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("📊 Toplam Kayıt", len(veriler))

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
    """Taraftar grupları panelini gösterir."""
    st.subheader("👥 Taraftar Grupları")

    gruplar = config["taraftar_gruplari"]
    cols = st.columns(len(gruplar))

    for i, grup in enumerate(gruplar):
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"### {grup['ad']}")
                st.write(f"**Takım:** {grup['takim']}")
                st.write(f"**Renkler:** {', '.join(grup['renkler'])}")

                # Platform linkleri
                for platform, kullanici in grup.get("platformlar", {}).items():
                    if platform == "twitter":
                        url = f"https://twitter.com/{kullanici}"
                        st.link_button(f"🐦 Twitter", url)
                    elif platform == "instagram":
                        url = f"https://instagram.com/{kullanici}"
                        st.link_button(f"📷 Instagram", url)
                    elif platform == "facebook":
                        url = f"https://facebook.com/{kullanici}"
                        st.link_button(f"📘 Facebook", url)

    st.divider()

def spor_branslari_paneli(config):
    """Spor branşları panelini gösterir."""
    st.subheader("🏆 Amasya Spor Branşları")

    branslar = config["spor_branslari"]

    for brans in branslar:
        with st.expander(f"{brans['ad']} {'⭐' if brans['oncelik'] == 1 else ''}"):
            col1, col2 = st.columns([2, 3])

            with col1:
                st.write(f"**Federasyon:** {brans['federasyon']}")
                st.write(f"**Takımlar:** {', '.join(brans['takimlar'])}")
                st.write(f"**Öncelik:** {'Yüksek' if brans['oncelik'] == 1 else 'Normal'}")

            with col2:
                st.info(f"**Amasya Başarıları:** {brans['amasya_basarilari']}")

    st.divider()

def disa_aktar_paneli(veriler):
    """Dışa aktarma panelini gösterir."""
    st.subheader("💾 Dışa Aktar")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("📄 CSV İndir", use_container_width=True):
            if veriler:
                df = pd.DataFrame(veriler)
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="CSV Dosyasını İndir",
                    data=csv,
                    file_name="amasya_spor_veriler.csv",
                    mime="text/csv"
                )
            else:
                st.warning("Aktarılacak veri yok!")

    with col2:
        if st.button("📊 Excel İndir", use_container_width=True):
            if veriler:
                df = pd.DataFrame(veriler)
                # JSON içeren sütunları string'e çevir
                for col in df.columns:
                    if df[col].dtype == 'object':
                        df[col] = df[col].astype(str)
                excel_buffer = df.to_excel(index=False, engine='openpyxl')
                st.download_button(
                    label="Excel Dosyasını İndir",
                    data=excel_buffer,
                    file_name="amasya_spor_veriler.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("Aktarılacak veri yok!")

    st.divider()

def tarama_ekrani(config):
    """Tarama ekranını gösterir ve verileri toplar."""
    st.title("🔄 Kaynaklar Taranıyor...")

    progress_bar = st.progress(0)
    durum_text = st.empty()

    def progress_callback(mevcut, toplam, mesaj):
        progress = int((mevcut / toplam) * 100)
        progress_bar.progress(progress)
        durum_text.text(f"{mevcut}/{toplam} - {mesaj}")

    # Verileri topla
    yeni_veriler = tum_verileri_topla(config, progress_callback)

    # Verileri işle
    durum_text.text("Veriler işleniyor...")
    yeni_veriler = verileri_isle(yeni_veriler, config)

    # Cache ile birleştir
    cache = cache_oku()
    cache = verileri_birlestir(yeni_veriler, cache)
    cache_yaz(cache)

    progress_bar.empty()
    durum_text.empty()

    st.success(f"✅ Tarama tamamlandı! {cache['istatistikler']['son_eklenen']} yeni kayıt bulundu.")
    st.info(f"📊 Toplam kayıt sayısı: {cache['istatistikler']['toplam_kayit']}")

    time.sleep(2)
    st.rerun()

def ana_ekran(config, cache):
    """Ana ekranı gösterir."""
    # Başlık
    st.title(f"{LOGO_EMOJI} Amasya Spor Radar")
    st.caption("Amasya'daki tüm sportif faaliyetleri, haberleri, etkinlikleri ve taraftar oluşumlarını takip eden istihbarat sistemi.")

    # Sekmeler
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📰 Haberler & Etkinlikler", 
        "👥 Taraftar Grupları", 
        "🏆 Spor Branşları",
        "📊 İstatistikler",
        "💾 Dışa Aktar"
    ])

    veriler = cache.get("veriler", [])

    with tab1:
        if not veriler:
            st.info("📭 Henüz veri yok. Lütfen soldaki menüden 'TÜM KAYNAKLARI TARA' butonuna basın.")
            st.markdown("""
            ### 🚀 Başlangıç
            1. Soldaki sidebar'dan **"🔄 TÜM KAYNAKLARI TARA"** butonuna basın
            2. Sistem 38+ kaynağı tarayacak
            3. Sonuçlar burada listelenecek
            4. Filtrelerle aradığınızı bulun
            """)
        else:
            # İstatistik paneli
            istatistik_paneli(veriler, config)

            # Filtreleri uygula
            filtreler = {
                "kategori": st.session_state.get("filtre_kategori", "Tümü"),
                "tur": st.session_state.get("filtre_tur", "Tümü"),
                "brans": st.session_state.get("filtre_brans", "Tümü"),
                "grup": st.session_state.get("filtre_grup", "Tümü"),
                "duygu": st.session_state.get("filtre_duygu", "Tümü"),
                "tarih": st.session_state.get("filtre_tarih", "Tümü"),
                "arama": st.session_state.get("arama", "")
            }

            filtrelenmis = verileri_filtrele(veriler, filtreler, config)

            st.subheader(f"📋 Sonuçlar ({len(filtrelenmis)} kayıt)")

            if not filtrelenmis:
                st.warning("Seçili filtrelere uygun kayıt bulunamadı.")
            else:
                # Sayfalama
                sayfa_basina = config["ayarlar"].get("sayfa_basina_kayit", 20)
                toplam_sayfa = max(1, (len(filtrelenmis) + sayfa_basina - 1) // sayfa_basina)

                sayfa = st.number_input("Sayfa", min_value=1, max_value=toplam_sayfa, value=1, key="sayfa")
                baslangic = (sayfa - 1) * sayfa_basina
                bitis = min(baslangic + sayfa_basina, len(filtrelenmis))

                st.caption(f"Gösterilen: {baslangic + 1}-{bitis} / Toplam: {len(filtrelenmis)}")

                for veri in filtrelenmis[baslangic:bitis]:
                    haber_karti_goster(veri, config)

    with tab2:
        taraftar_gruplari_paneli(config)

        # Taraftar gruplarına ait haberler
        st.subheader("📰 Taraftar Grupları İlgili Haberler")
        for grup in config["taraftar_gruplari"]:
            grup_haberleri = [v for v in veriler if any(g["ad"] == grup["ad"] for g in v.get("taraftar_gruplari", []))]
            if grup_haberleri:
                with st.expander(f"{grup['ad']} - {len(grup_haberleri)} haber"):
                    for haber in grup_haberleri[:5]:
                        st.markdown(f"- [{haber.get('baslik', '')}]({haber.get('link', '#')}) - {haber.get('kaynak_ad', '')}")

    with tab3:
        spor_branslari_paneli(config)

        # Branşlara ait haberler
        st.subheader("📰 Spor Branşları İlgili Haberler")
        for brans in config["spor_branslari"]:
            brans_haberleri = [v for v in veriler if any(b["ad"] == brans["ad"] for b in v.get("spor_branslari", []))]
            if brans_haberleri:
                with st.expander(f"{brans['ad']} - {len(brans_haberleri)} haber"):
                    for haber in brans_haberleri[:5]:
                        st.markdown(f"- [{haber.get('baslik', '')}]({haber.get('link', '#')}) - {haber.get('kaynak_ad', '')}")

    with tab4:
        st.subheader("📊 Genel İstatistikler")

        if veriler:
            # Kaynak dağılımı
            kaynak_dagilimi = defaultdict(int)
            for v in veriler:
                kaynak_dagilimi[v.get("kaynak_ad", "Bilinmiyor")] += 1

            st.write("**Kaynak Dağılımı:**")
            for kaynak, sayi in sorted(kaynak_dagilimi.items(), key=lambda x: x[1], reverse=True)[:10]:
                st.write(f"- {kaynak}: {sayi} kayıt")

            # Duygu dağılımı
            duygu_dagilimi = defaultdict(int)
            for v in veriler:
                duygu_dagilimi[v.get("duygu", "nötr")] += 1

            st.write("**Duygu Dağılımı:**")
            for duygu, sayi in duygu_dagilimi.items():
                emoji = {"olumlu": "🟢", "olumsuz": "🔴", "nötr": "⚪"}.get(duygu, "⚪")
                st.write(f"- {emoji} {duygu}: {sayi}")

            # Branş dağılımı
            brans_dagilimi = defaultdict(int)
            for v in veriler:
                for b in v.get("spor_branslari", []):
                    brans_dagilimi[b["ad"]] += 1

            if brans_dagilimi:
                st.write("**Branş Dağılımı:**")
                for brans, sayi in sorted(brans_dagilimi.items(), key=lambda x: x[1], reverse=True):
                    st.write(f"- {brans}: {sayi} haber")
        else:
            st.info("Henüz istatistik için yeterli veri yok.")

    with tab5:
        disa_aktar_paneli(veriler)

# =============================================================================
# ANA PROGRAM
# =============================================================================

def main():
    """Ana program akışı."""
    sayfa_yapilandir()

    # Config oku
    config = config_oku()
    if not config:
        st.error("""
        ❌ **config.json dosyası bulunamadı!**

        Lütfen aşağıdaki adımları takip edin:
        1. `config.json` dosyasını bu uygulamanın olduğu klasöre koyun
        2. Sayfayı yenileyin (F5)

        **Dosya yapısı şöyle olmalı:**
        ```
        klasör/
        ├── amasya_spor.py
        ├── config.json
        └── cache.json (otomatik oluşur)
        ```
        """)
        return

    # Cache oku
    cache = cache_oku()

    # Sidebar ve filtreler
    sidebar_sonuc = sidebar_filtreler(config, cache)

    # Tarama isteği kontrolü
    if sidebar_sonuc == "tara":
        tarama_ekrani(config)
        return

    # Ana ekran
    ana_ekran(config, cache)

if __name__ == "__main__":
    main()
