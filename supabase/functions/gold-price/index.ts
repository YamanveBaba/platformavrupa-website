// Supabase Edge Function: Altın Fiyatları
// Bu fonksiyon backend'den finans API'lerine ve web scraping yapar (CORS sorunsuz)

Deno.serve(async (req) => {
  // CORS headers
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
  };

  // OPTIONS request için CORS preflight
  if (req.method === 'OPTIONS') {
    return new Response('ok', { 
      status: 200, // HTTP ok status (tarayıcılar bunu bekliyor)
      headers: {
        ...headers,
        'Access-Control-Max-Age': '86400' // 24 saat cache
      }
    });
  }

  try {
    console.log('🔄 Altın fiyatları çekiliyor (backend)...');

    // 1. Öncelik: anlikaltinfiyatlari.com'dan direkt fiyatları çek
    let goldData = await fetchFromAnlikAltinFiyatlari();
    
    // 2. Başarısız olursa Metals API'den ons fiyatı çek (formül ile hesapla)
    if (!goldData || !goldData.prices || Object.keys(goldData.prices).length === 0) {
      console.log('⚠️ anlikaltinfiyatlari.com başarısız, Metals API deneniyor...');
      const onsPrice = await fetchFromMetalsAPI();
      if (onsPrice && onsPrice > 0) {
        goldData = { ons: onsPrice, prices: null, source: 'metals-api', needsCalculation: true };
      }
    }
    
    // 3. Başarısız olursa FreeGoldAPI dene
    if (!goldData || (!goldData.prices && !goldData.needsCalculation)) {
      console.log('⚠️ Metals API başarısız, FreeGoldAPI deneniyor...');
      const onsPrice = await fetchFromFreeGoldAPI();
      if (onsPrice && onsPrice > 0) {
        goldData = { ons: onsPrice, prices: null, source: 'freegoldapi', needsCalculation: true };
      }
    }
    
    // 4. Başarısız olursa TCMB'den dene
    if (!goldData || (!goldData.prices && !goldData.needsCalculation)) {
      console.log('⚠️ FreeGoldAPI başarısız, TCMB deneniyor...');
      const onsPrice = await fetchFromTCMB();
      if (onsPrice && onsPrice > 0) {
        goldData = { ons: onsPrice, prices: null, source: 'tcmb', needsCalculation: true };
      }
    }
    
    // 5. Hala başarısız olursa hata döndür (gömülü fiyat YOK)
    if (!goldData || (!goldData.prices && !goldData.needsCalculation)) {
      console.error('❌ Tüm kaynaklardan altın fiyatı alınamadı');
      return new Response(
        JSON.stringify({ 
          error: 'Altın fiyatları alınamadı', 
          prices: null,
          message: 'Lütfen daha sonra tekrar deneyin.'
        }),
        { 
          status: 500, 
          headers: { ...headers, 'Content-Type': 'application/json' } 
        }
      );
    }

    // Response formatını oluştur
    const response = {
      ons: goldData.ons || null,
      prices: goldData.prices || null,
      source: goldData.source || 'unknown',
      needsCalculation: goldData.needsCalculation || false,
      timestamp: new Date().toISOString()
    };

    console.log(`✅ Altın fiyatları alındı: ${goldData.source}`);
    if (goldData.prices) {
      console.log(`   Gram Altın: ${goldData.prices.gram?.toFixed(2)} TL`);
    } else if (goldData.ons) {
      console.log(`   Ons Altın: ${goldData.ons.toFixed(2)} USD (hesaplama gerekli)`);
    }

    return new Response(
      JSON.stringify(response),
      { 
        headers: { ...headers, 'Content-Type': 'application/json' } 
      }
    );
  } catch (error) {
    console.error('❌ Edge Function hatası:', error);
    return new Response(
      JSON.stringify({ 
        error: error.message, 
        prices: null,
        message: 'Bir hata oluştu. Lütfen daha sonra tekrar deneyin.'
      }),
      { 
        status: 500, 
        headers: { ...headers, 'Content-Type': 'application/json' } 
      }
    );
  }
});

// anlikaltinfiyatlari.com'dan direkt altın fiyatlarını çek
async function fetchFromAnlikAltinFiyatlari(): Promise<{ ons: number | null, prices: any, source: string } | null> {
  try {
    console.log('   📡 anlikaltinfiyatlari.com scraping başlatılıyor...');
    
    const response = await fetch('https://anlikaltinfiyatlari.com/', {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
      },
    });

    if (!response.ok) {
      console.warn('   ⚠️ anlikaltinfiyatlari.com HTTP hatası:', response.status);
      return null;
    }

    const html = await response.text();
    
    // HTML'den fiyatları parse et (tablo formatından)
    const prices: any = {};
    
    // Helper function: Fiyat çıkarma
    const extractPrice = (text: string, pattern: RegExp, min: number, max: number): number | null => {
      const match = text.match(pattern);
      if (match) {
        const priceStr = match[1] || match[2] || match[0];
        const price = parseFloat(priceStr.replace(/[^\d.,]/g, '').replace(',', '.'));
        if (!isNaN(price) && price >= min && price <= max) {
          return price;
        }
      }
      return null;
    };
    
    // Gram Altın - tablo satırından FİYAT sütununu bul
    const gramPrice = extractPrice(html, /Gram\s+Altın[^>]*>[\s\S]{0,2000}?<td[^>]*>[\s\S]{0,200}?(\d{3,5}[.,]\d{2,4})/i, 1000, 100000) ||
                      extractPrice(html, /Gram\s+Altın[^>]*>[\s\S]{0,1000}?(\d{3,5}[.,]\d{2,4})/i, 1000, 100000);
    if (gramPrice) prices.gram = gramPrice;
    
    // Çeyrek Altın
    const ceyrekPrice = extractPrice(html, /Çeyrek\s+Altın[^>]*>[\s\S]{0,2000}?<td[^>]*>[\s\S]{0,200}?(\d{4,6}[.,]\d{2,4})/i, 5000, 200000) ||
                        extractPrice(html, /Çeyrek\s+Altın[^>]*>[\s\S]{0,1000}?(\d{4,6}[.,]\d{2,4})/i, 5000, 200000);
    if (ceyrekPrice) prices.ceyrek = ceyrekPrice;
    
    // Yarım Altın
    const yarimPrice = extractPrice(html, /Yarım\s+Altın[^>]*>[\s\S]{0,2000}?<td[^>]*>[\s\S]{0,200}?(\d{4,6}[.,]\d{2,4})/i, 10000, 500000) ||
                       extractPrice(html, /Yarım\s+Altın[^>]*>[\s\S]{0,1000}?(\d{4,6}[.,]\d{2,4})/i, 10000, 500000);
    if (yarimPrice) prices.yarim = yarimPrice;
    
    // Tam Altın
    const tamPrice = extractPrice(html, /Tam\s+Altın[^>]*>[\s\S]{0,2000}?<td[^>]*>[\s\S]{0,200}?(\d{4,6}[.,]\d{2,4})/i, 20000, 1000000) ||
                     extractPrice(html, /Tam\s+Altın[^>]*>[\s\S]{0,1000}?(\d{4,6}[.,]\d{2,4})/i, 20000, 1000000);
    if (tamPrice) prices.tam = tamPrice;
    
    // Cumhuriyet Altını
    const cumhuriyetPrice = extractPrice(html, /Cumhuriyet\s+Altını[^>]*>[\s\S]{0,2000}?<td[^>]*>[\s\S]{0,200}?(\d{4,6}[.,]\d{2,4})/i, 20000, 1000000) ||
                            extractPrice(html, /Cumhuriyet\s+Altını[^>]*>[\s\S]{0,1000}?(\d{4,6}[.,]\d{2,4})/i, 20000, 1000000);
    if (cumhuriyetPrice) prices.cumhuriyet = cumhuriyetPrice;
    
    // Ata Altın
    const ataPrice = extractPrice(html, /Ata\s+Altın[^>]*>[\s\S]{0,2000}?<td[^>]*>[\s\S]{0,200}?(\d{4,6}[.,]\d{2,4})/i, 20000, 1000000) ||
                     extractPrice(html, /ATA\s+ALTIN[^>]*>[\s\S]{0,1000}?(\d{4,6}[.,]\d{2,4})/i, 20000, 1000000);
    if (ataPrice) prices.ata = ataPrice;
    
    // Gremse Altın
    const gremsePrice = extractPrice(html, /Gremse\s+Altın[^>]*>[\s\S]{0,2000}?<td[^>]*>[\s\S]{0,200}?(\d{5,7}[.,]\d{2,4})/i, 50000, 2000000) ||
                        extractPrice(html, /Gremse\s+Altın[^>]*>[\s\S]{0,1000}?(\d{5,7}[.,]\d{2,4})/i, 50000, 2000000);
    if (gremsePrice) prices.gremse = gremsePrice;
    
    // Reşat Altın
    const resatPrice = extractPrice(html, /Reşat\s+Altın[^>]*>[\s\S]{0,2000}?<td[^>]*>[\s\S]{0,200}?(\d{4,6}[.,]\d{2,4})/i, 20000, 1000000) ||
                       extractPrice(html, /Reşat\s+Altın[^>]*>[\s\S]{0,1000}?(\d{4,6}[.,]\d{2,4})/i, 20000, 1000000);
    if (resatPrice) prices.resat = resatPrice;
    
    // 14 Ayar Altın
    const ayar14Price = extractPrice(html, /14\s+Ayar\s+Altın[^>]*>[\s\S]{0,2000}?<td[^>]*>[\s\S]{0,200}?(\d{3,5}[.,]\d{2,4})/i, 1000, 100000) ||
                        extractPrice(html, /14\s+Ayar\s+Altın[^>]*>[\s\S]{0,1000}?(\d{3,5}[.,]\d{2,4})/i, 1000, 100000);
    if (ayar14Price) prices.bilezik14 = ayar14Price;
    
    // 18 Ayar Altın
    const ayar18Price = extractPrice(html, /18\s+Ayar\s+Altın[^>]*>[\s\S]{0,2000}?<td[^>]*>[\s\S]{0,200}?(\d{3,5}[.,]\d{2,4})/i, 1000, 100000) ||
                        extractPrice(html, /18\s+Ayar\s+Altın[^>]*>[\s\S]{0,1000}?(\d{3,5}[.,]\d{2,4})/i, 1000, 100000);
    if (ayar18Price) prices.bilezik18 = ayar18Price;
    
    // 22 Ayar Altın
    const ayar22Price = extractPrice(html, /22\s+Ayar\s+Altın[^>]*>[\s\S]{0,2000}?<td[^>]*>[\s\S]{0,200}?(\d{3,5}[.,]\d{2,4})/i, 1000, 100000) ||
                        extractPrice(html, /22\s+Ayar\s+Altın[^>]*>[\s\S]{0,1000}?(\d{3,5}[.,]\d{2,4})/i, 1000, 100000);
    if (ayar22Price) prices.bilezik22 = ayar22Price;
    
    // Ons Altın (TL cinsinden)
    const onsPrice = extractPrice(html, /Altın\s+Ons[^>]*>[\s\S]{0,2000}?<td[^>]*>[\s\S]{0,200}?(\d{4,5}[.,]\d{2,4})/i, 4000, 6000) ||
                     extractPrice(html, /ONS\s+ALTIN[^>]*>[\s\S]{0,1000}?(\d{4,5}[.,]\d{2,4})/i, 4000, 6000);
    const ons = onsPrice || null;
    
    // En az gram altın fiyatı bulunmalı (zorunlu)
    if (!prices.gram || prices.gram <= 0) {
      console.warn('   ⚠️ Gram altın fiyatı bulunamadı');
      return null;
    }
    
    // En az 3 fiyat bulunmalı (başarı kriteri)
    const foundPrices = Object.keys(prices).filter(k => k !== 'gram' && prices[k] > 0);
    if (foundPrices.length < 2) {
      console.warn('   ⚠️ Yeterli altın fiyatı bulunamadı (sadece gram bulundu)');
      // Sadece gram varsa bile döndürelim, diğerleri formülle hesaplanabilir
    }
    
    console.log(`   ✅ ${Object.keys(prices).length} altın fiyatı bulundu`);
    
    return {
      ons: ons,
      prices: prices,
      source: 'anlikaltinfiyatlari.com'
    };
    
  } catch (error) {
    console.error('   ❌ anlikaltinfiyatlari.com scraping hatası:', error.message);
    return null;
  }
}

// Metals API'den ons fiyatı çek
async function fetchFromMetalsAPI(): Promise<number | null> {
  try {
    const response = await fetch('https://api.metals.live/v1/spot/gold', {
      headers: {
        'User-Agent': 'PlatformAvrupa/1.0',
      },
    });

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    
    // Metals API formatı: { price: 2800.50, ... } veya [{ price: 2800.50, ... }]
    if (data.price && typeof data.price === 'number' && data.price > 1000 && data.price < 5000) {
      return data.price;
    }
    
    if (Array.isArray(data) && data.length > 0 && data[0].price) {
      const price = data[0].price;
      if (price > 1000 && price < 5000) {
        return price;
      }
    }

    return null;
  } catch (error) {
    console.error('Metals API hatası:', error);
    return null;
  }
}

// FreeGoldAPI'den ons fiyatı çek
async function fetchFromFreeGoldAPI(): Promise<number | null> {
  try {
    const response = await fetch('https://freegoldapi.com/data/latest.json', {
      headers: {
        'User-Agent': 'PlatformAvrupa/1.0',
      },
    });

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    
    // FreeGoldAPI formatı: { price: 2800.50, currency: "USD", ... }
    if (data.price && typeof data.price === 'number' && data.price > 1000 && data.price < 5000) {
      return data.price;
    }

    return null;
  } catch (error) {
    console.error('FreeGoldAPI hatası:', error);
    return null;
  }
}

// TCMB'den ons fiyatı çek (TRY cinsinden, sonra USD'ye çevir)
async function fetchFromTCMB(): Promise<number | null> {
  try {
    const response = await fetch('https://www.tcmb.gov.tr/kurlar/today.xml', {
      headers: {
        'User-Agent': 'PlatformAvrupa/1.0',
      },
    });

    if (!response.ok) {
      return null;
    }

    const xmlText = await response.text();
    
    // XAU (Altın) için arama
    const xauMatch = xmlText.match(/<Currency[^>]*Code\s*=\s*["']XAU["'][^>]*>([\s\S]*?)<\/Currency>/i);
    if (!xauMatch) {
      return null;
    }

    const xauData = xauMatch[1];
    const buyingMatch = xauData.match(/<ForexBuying[^>]*>([^<]+)<\/ForexBuying>/i);
    if (!buyingMatch) {
      return null;
    }

    const onsAltinTry = parseFloat(buyingMatch[1].replace(',', '.').replace(/[^\d.]/g, ''));
    if (isNaN(onsAltinTry) || onsAltinTry <= 0) {
      return null;
    }

    // USD/TRY kuru al
    const usdMatch = xmlText.match(/<Currency[^>]*Code\s*=\s*["']USD["'][^>]*>([\s\S]*?)<\/Currency>/i);
    if (!usdMatch) {
      return null;
    }

    const usdData = usdMatch[1];
    const usdBuyingMatch = usdData.match(/<ForexBuying[^>]*>([^<]+)<\/ForexBuying>/i);
    if (!usdBuyingMatch) {
      return null;
    }

    const usdTry = parseFloat(usdBuyingMatch[1].replace(',', '.').replace(/[^\d.]/g, ''));
    if (isNaN(usdTry) || usdTry <= 0) {
      return null;
    }

    // Ons fiyatını TRY'den USD'ye çevir
    const onsUsd = onsAltinTry / usdTry;
    
    if (onsUsd > 1000 && onsUsd < 5000) {
      return onsUsd;
    }

    return null;
  } catch (error) {
    console.error('TCMB hatası:', error);
    return null;
  }
}
