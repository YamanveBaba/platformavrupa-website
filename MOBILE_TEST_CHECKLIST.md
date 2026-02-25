# 📱 Mobil Test Kontrol Listesi - Yol Arkadaşı

Bu belge, Yol Arkadaşı modülünün gerçek cihazlarda test edilmesi için bir rehberdir.

---

## 📋 Test Senaryoları

### 1. 🚗 Yol Arkadaşı Ana Sayfa (`yol_arkadasi.html`)

#### Görsel Kontroller
- [ ] Filtreleme bölümü mobilde düzgün görünüyor mu?
- [ ] Yolculuk kartları dikey sıralanıyor mu?
- [ ] "İlan Ver" butonu erişilebilir mi?
- [ ] Kartlar dokunmaya duyarlı mı?

#### Fonksiyonel Testler
1. **Filtreleme**
   - [ ] Ülke seçimi yapılabiliyor mu?
   - [ ] Şehir dropdown'ları çalışıyor mu?
   - [ ] Tarih seçimi yapılabiliyor mu?
   - [ ] "Ara" butonu çalışıyor mu?

2. **Yolculuk Detayı**
   - [ ] Kart tıklanınca modal açılıyor mu?
   - [ ] Modal içeriği okunabilir mi?
   - [ ] "X" butonu ile kapatılabiliyor mu?
   - [ ] Scroll yapılabiliyor mu?

3. **Rezervasyon**
   - [ ] "Rezervasyon Talebi Gönder" butonu görünüyor mu?
   - [ ] Butona tıklanabiliyor mu?
   - [ ] Koltuk sayısı seçimi açılıyor mu?
   - [ ] Başarı mesajı gösteriliyor mu?
   - [ ] Sürücü telefonu okunabilir mi?

#### Test Adımları
```
1. Mobil tarayıcıdan yol_arkadasi.html'e git
2. Filtreleme yap (örn: Almanya -> Türkiye)
3. Bir yolculuk kartına tıkla
4. Modal'ı incele
5. "Rezervasyon Talebi Gönder" butonuna tıkla
6. Giriş yap (gerekirse)
7. Koltuk sayısı seç
8. Sürücü telefon numarasını kontrol et
```

---

### 2. 📝 İlan Ver Sayfası (`yol_ilan_ver.html`)

#### Görsel Kontroller
- [ ] Form bölümleri düzgün görünüyor mu?
- [ ] Rota bilgileri sol-sağ kolonlarda mı? (tablet/masaüstü)
- [ ] Mobilde dikey mi? (telefon)
- [ ] Input alanları dokunmaya uygun mu?
- [ ] Checkbox'lar ve toggle'lar çalışıyor mu?

#### Fonksiyonel Testler

1. **Rota Bilgileri**
   - [ ] Nereden ülke seçilebiliyor mu?
   - [ ] Nereden şehir otomatik yükleniyor mu?
   - [ ] Nereye ülke seçilebiliyor mu?
   - [ ] Nereye şehir otomatik yükleniyor mu?
   - [ ] Tarih seçimi yapılabiliyor mu? (bugünden önce seçilemiyor olmalı)
   - [ ] Saat dropdown'ı 15 dakika aralıklarında mı?

2. **Ara Durak Ekleme**
   - [ ] "Ara Durak Ekle" butonu çalışıyor mu?
   - [ ] Modal açılıyor mu?
   - [ ] Ülke ve şehir seçilebiliyor mu?
   - [ ] Ara durak listeye ekleniyor mu?
   - [ ] Eklenen durak silinebiliyor mu?
   - [ ] Maksimum 5 durak eklenebiliyor mu?

3. **Araç Bilgileri**
   - [ ] Marka seçilebiliyor mu?
   - [ ] Model dropdown'ı otomatik dolduruluyor mu?
   - [ ] Koltuk sayısı seçilebiliyor mu?
   - [ ] Fiyat girilebiliyor mu?

4. **Yolculuk Tercihleri**
   - [ ] Toggle switch'ler çalışıyor mu?
   - [ ] Kargo kabul toggle'ı çalışıyor mu?
   - [ ] Sigara içilmez toggle'ı çalışıyor mu?
   - [ ] Müzik toggle'ı çalışıyor mu?
   - [ ] Evcil hayvan toggle'ı çalışıyor mu?

5. **İletişim Bilgileri**
   - [ ] Ülke kodu dropdown'ı çalışıyor mu?
   - [ ] Telefon numarası girilebiliyor mu?
   - [ ] Ek notlar yazılabiliyor mu?

6. **Güvenlik Onayı**
   - [ ] Checkbox tıklanabiliyor mu?
   - [ ] Submit butonu aktifleşiyor mu?
   - [ ] Form gönderiliyor mu?
   - [ ] Başarı mesajı gösteriliyor mu?

#### Test Adımları
```
1. Mobil tarayıcıdan yol_ilan_ver.html'e git
2. Tüm alanları doldur:
   - Nereden: Almanya - Berlin
   - Nereye: Türkiye - İstanbul
   - Tarih: [Yarının tarihi]
   - Saat: 08:00
   - Ara Durak: Avusturya - Viyana
   - Araç: Mercedes - E-Class
   - Koltuk: 3
   - Fiyat: 100
3. Toggle'ları değiştir
4. Telefon gir: +49 123 456 7890
5. Güvenlik checkbox'ını işaretle
6. Formu gönder
7. Başarı mesajını kontrol et
```

---

### 3. 👨‍💼 Admin Panel (`admin.html`)

#### Test için Gerekli: Admin Hesabı

#### Görsel Kontroller
- [ ] Yan menü mobilde gizlenebiliyor mu?
- [ ] Rezervasyon kartları okunabilir mi?
- [ ] İstatistik kutuları düzgün görünüyor mu?
- [ ] Scroll çalışıyor mu?

#### Fonksiyonel Testler

1. **Rezervasyon Listesi**
   - [ ] "Yolculuk & Kargo" menüsüne tıkla
   - [ ] "Rezervasyonları Yükle" butonu çalışıyor mu?
   - [ ] Rezervasyonlar listeleniyor mu?
   - [ ] İstatistikler doğru gösteriliyor mu? (Bekleyen, Onaylı, Reddedilen, Toplam)

2. **Rezervasyon Detayları**
   - [ ] Yolcu adı görünüyor mu?
   - [ ] Yolcu telefonu görünüyor mu?
   - [ ] Sürücü adı görünüyor mu?
   - [ ] Sürücü telefonu görünüyor mu?
   - [ ] Rota bilgisi görünüyor mu?
   - [ ] Tarih görünüyor mu?
   - [ ] Koltuk sayısı görünüyor mu?
   - [ ] Durum (pending/approved/rejected) görünüyor mu?

3. **Realtime Test**
   - [ ] Admin paneli bir cihazda aç
   - [ ] Başka bir cihazdan rezervasyon yap
   - [ ] Admin panelinde otomatik güncellenme oluyor mu?
   - [ ] İstatistikler güncelleniyor mu?

#### Test Adımları
```
1. Admin hesabı ile giriş yap
2. Yan menüden "Yolculuk & Kargo" seç
3. Rezervasyon bölümüne scroll yap
4. "Rezervasyonları Yükle" butonuna tıkla
5. Listelenen rezervasyonları incele
6. İstatistikleri kontrol et
7. Başka bir cihazdan yeni rezervasyon yap
8. Admin panelinin otomatik güncellendiğini gör
```

---

## 📐 Responsive Breakpoint Testleri

### Mobil (< 768px)
- [ ] Form elemanları tek kolon halinde
- [ ] Butonlar tam genişlik
- [ ] Filtreleme bölümü dikey sıralı
- [ ] Kartlar dikey sıralı

### Tablet (768px - 1024px)
- [ ] İlan ver sayfası 2 kolonlu
- [ ] Yolculuk kartları 2 kolonlu
- [ ] Filtreleme elemanları yan yana

### Masaüstü (> 1024px)
- [ ] Yolculuk kartları 3 kolonlu
- [ ] Tüm form elemanları yan yana
- [ ] Admin panel yan menü her zaman açık

---

## 🌐 Tarayıcı Testleri

### iOS (Safari)
- [ ] Modal açılıyor mu?
- [ ] Date picker çalışıyor mu?
- [ ] Toggle switch'ler dokunmaya duyarlı mı?
- [ ] SweetAlert popup'ları düzgün görünüyor mu?

### Android (Chrome)
- [ ] Tüm form elemanları çalışıyor mu?
- [ ] Scroll performansı iyi mi?
- [ ] Keyboard açıldığında layout bozulmuyor mu?
- [ ] Back butonu çalışıyor mu?

### Mobil Tarayıcı Özellikleri
- [ ] Zoom yapılabiliyor mu?
- [ ] Yatay mod çalışıyor mu?
- [ ] Offline'da ne oluyor? (Supabase bağlantı hatası)

---

## 🐛 Yaygın Sorunları Kontrol Et

### Mobil Sorunlar
- [ ] Butonlar çok küçük değil mi? (minimum 44x44px)
- [ ] Metin okunabilir mi? (minimum 16px)
- [ ] Form elemanları kolayca tıklanabiliyor mu?
- [ ] Loading state'leri görünüyor mu?

### iOS Özel Sorunlar
- [ ] Fixed position elemanlar çalışıyor mu?
- [ ] Input focus'ta zoom yapıyor mu? (font-size: 16px olmalı)
- [ ] Date input Safari'de düzgün görünüyor mu?

### Android Özel Sorunlar
- [ ] Back button davranışı doğru mu?
- [ ] Keyboard input type'ları doğru mu? (tel, email, date)
- [ ] Select dropdown'ları native görünüyor mu?

---

## ✅ Test Sonuçları Şablonu

```
TARİH: ___________
CİHAZ: ___________
OS/TARAYICI: ___________
EKRAN BOYUTU: ___________

[ ] Yol Arkadaşı Ana Sayfa - BAŞARILI / BAŞARISIZ
    Notlar: ___________

[ ] İlan Ver Sayfası - BAŞARILI / BAŞARISIZ
    Notlar: ___________

[ ] Admin Panel - BAŞARILI / BAŞARISIZ
    Notlar: ___________

[ ] Responsive Davranış - BAŞARILI / BAŞARISIZ
    Notlar: ___________

GENEL NOTLAR:
___________
___________
```

---

## 📞 Test Senaryosu - Tam Akış

### Senaryo: Yolcu Rezervasyon Yapar

1. **Başlangıç**
   - Kullanıcı telefonda `yol_arkadasi.html`'e girer
   - Almanya'dan Türkiye'ye yolculuk arar
   - Filtreyi uygular

2. **Yolculuk Seçimi**
   - Uygun bir yolculuk kartına tıklar
   - Modal açılır, detayları görür
   - "Rezervasyon Talebi Gönder" butonuna tıklar

3. **Rezervasyon**
   - Giriş yapmamışsa login sayfasına yönlendirilir
   - Giriş yapar
   - Koltuk sayısı seçer (2 koltuk)
   - Onaylar

4. **Sonuç**
   - Başarı mesajı görür
   - Sürücünün telefon numarasını görür: "+49 123 456 7890"
   - Sürücü adını görür
   - "Admin panelinde görüntülenecek" bilgisini okur

5. **Admin Panelinde**
   - Admin hesabı ile giriş yapar
   - Yeni rezervasyonu görür
   - Bekleyen sayısı 1 arttı
   - Yolcu ve sürücü bilgileri doğru görünüyor

**BEKLENEN SÜRE:** < 2 dakika  
**BEKLENEN BAŞARI:** %100

---

## 🎯 Kritik Başarı Kriterleri

Modülün "başarılı" sayılması için:

1. **✅ Rezervasyon yapılabiliyor** - Supabase'e kaydediliyor
2. **✅ Sürücü telefonu gösteriliyor** - Hemen, rezervasyon sonrası
3. **✅ İlan verilebiliyor** - Form gönderilebiliyor
4. **✅ Admin panelde görünüyor** - Reservations bölümünde
5. **✅ Mobilde kullanılabiliyor** - Layout bozulmuyor

Tüm bu kriterler karşılanıyorsa: **✅ MOD ÜL PRODUCTION HAZIR**

---

**Not:** Bu checklist'i yazdır ve gerçek cihazlarda test ederken kullan!
