# Sağlık Danışmanlık Başvuruları – Nereye Gidiyor, Nasıl Okuyup Cevap Verirsiniz?

## Başvurular nereye gidiyor?

Kullanıcılar **“Başvuruyu Gönder”** dediğinde veriler **Supabase** veritabanındaki **`health_leads`** tablosuna kaydedilir. Fotoğraflar (varsa) **Supabase Storage** içindeki **`health-lead-photos`** bucket’ına yüklenir.

---

## Başvuruları nasıl okuyacaksınız?

### 1. Admin panel (önerilen)

- **admin.html** sayfasını açın (admin yetkisi gerekir).
- Soldan **“Sağlık Turizmi”** sekmesine tıklayın.
- **Lead’ler** (danışmanlık başvuruları) burada listelenir:
  - Ad soyad, referans kodu, kategori, tedavi tipi, klinik, ülke, teklif, komisyon
  - **WhatsApp** butonu ile doğrudan başvuru sahibine mesaj linki
  - **Not Ekle**, **Klinik Ata**, **Teklif Ekle**, **İletişime Geçildi** gibi işlemler

Buradan tüm başvuruları görebilir, filtreleyebilir ve yönetebilirsiniz.

### 2. Supabase Dashboard

- [Supabase](https://supabase.com) projenize girin.
- **Table Editor** → **`health_leads`** tablosunu açın.
- Tüm başvurular satır satır burada görünür (ad, e-posta, telefon, whatsapp, kategori, notlar, tarih vb.).

---

## Nasıl cevap vereceksiniz?

- Her başvuruda **telefon** ve **WhatsApp** numarası kayıtlı.
- **Admin panel** → Sağlık Turizmi → ilgili başvurunun yanındaki **WhatsApp** butonuna tıklayarak doğrudan o numaraya mesaj linki açabilirsiniz.
- İsterseniz başvurudaki telefon numarasını kopyalayıp arayabilir veya kendi WhatsApp’ınızdan yazabilirsiniz.
- Admin’den **“Not Ekle”** ile başvuruya sadece sizin gördüğünüz notlar ekleyebilir, **“İletişime Geçildi”** ile durumu güncelleyebilirsiniz.

Özet: Başvurular **Supabase `health_leads`** tablosunda; okumak ve yanıtlamak için **admin panel (Sağlık Turizmi)** kullanmanız yeterli.
