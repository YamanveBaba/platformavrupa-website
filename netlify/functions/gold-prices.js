// Netlify Function: Tüm altın fiyat kaynaklarını backend'den çek (CORS sorunu çözümü)
// Node.js fetch polyfill (Node 18+ için gerekli değil ama eski versiyonlar için)

exports.handler = async (event, context) => {
    // CORS headers
    const headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Content-Type': 'application/json'
    };

    // OPTIONS request için CORS
    if (event.httpMethod === 'OPTIONS') {
        return {
            statusCode: 200,
            headers,
            body: ''
        };
    }

    try {
        // Öncelik sırası: Vakıfbank API → TCMB API → Kuyumcu Scraping
        
        // 1. Vakıfbank API'den dene
        let goldData = await fetchVakifbankGoldPrices();
        
        // 2. Başarısız olursa TCMB'den dene
        if (!goldData || Object.keys(goldData).length === 0 || !goldData.gram) {
            goldData = await fetchTCMBGoldPrices();
        }
        
        // 3. Hala başarısız olursa kuyumcu scraping
        if (!goldData || Object.keys(goldData).length === 0 || !goldData.gram) {
            goldData = await scrapeAnlikAltinFiyati();
        }
        
        // 4. Son çare: doviz.com scraping
        if (!goldData || Object.keys(goldData).length === 0 || !goldData.gram) {
            goldData = await scrapeDovizCom();
        }
        
        if (!goldData || Object.keys(goldData).length === 0 || !goldData.gram) {
            return {
                statusCode: 404,
                headers,
                body: JSON.stringify({ error: 'Altın fiyatları alınamadı' })
            };
        }

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(goldData)
        };
    } catch (error) {
        console.error('Altın fiyatları hatası:', error);
        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({ error: 'Altın fiyatları alınamadı' })
        };
    }
};

// Vakıfbank API'den altın fiyatlarını çek
async function fetchVakifbankGoldPrices() {
    try {
        // Vakıfbank API endpoint (API key environment variable'dan alınabilir)
        const apiKey = process.env.VAKIFBANK_API_KEY || '';
        const endpoint = 'https://apiportal.vakifbank.com.tr/api/InformationServices/getGoldPrices';
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const response = await fetch(endpoint, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Authorization': apiKey ? `Bearer ${apiKey}` : ''
            },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const data = await response.json();
            console.log('✅ Vakıfbank API\'den altın fiyatları alındı');
            
            // Parse et
            if (data.data) {
                return {
                    gram: data.data.gramAltin || data.data.gram || 0,
                    ceyrek: data.data.ceyrekAltin || data.data.ceyrek || 0,
                    yarim: data.data.yarimAltin || data.data.yarim || 0,
                    tam: data.data.tamAltin || data.data.tam || data.data.ata || 0,
                    cumhuriyet: data.data.cumhuriyetAltin || data.data.cumhuriyet || 0,
                    resat: data.data.resatAltin || data.data.resat || 0,
                    bilezik22: data.data.bilezik22 || 0,
                    bilezik18: data.data.bilezik18 || 0,
                    bilezik14: data.data.bilezik14 || 0,
                    _changes: data.data.changes || {}
                };
            }
            
            return {
                gram: data.gramAltin || data.gram || 0,
                ceyrek: data.ceyrekAltin || data.ceyrek || 0,
                yarim: data.yarimAltin || data.yarim || 0,
                tam: data.tamAltin || data.tam || data.ata || 0,
                cumhuriyet: data.cumhuriyetAltin || data.cumhuriyet || 0,
                resat: data.resatAltin || data.resat || 0,
                bilezik22: data.bilezik22 || 0,
                bilezik18: data.bilezik18 || 0,
                bilezik14: data.bilezik14 || 0,
                _changes: data.changes || {}
            };
        }
    } catch (e) {
        console.warn('⚠️ Vakıfbank API hatası:', e.message);
    }
    return null;
}

// TCMB'den altın fiyatlarını çek
async function fetchTCMBGoldPrices() {
    try {
        const endpoint = 'https://www.tcmb.gov.tr/kurlar/today.xml';
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const response = await fetch(endpoint, {
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const xmlText = await response.text();
            console.log('✅ TCMB\'den altın fiyatları alındı');
            
            // XAU (Altın) için arama
            const xauMatch = xmlText.match(/<Currency[^>]*Code="XAU"[^>]*>([\s\S]*?)<\/Currency>/);
            if (!xauMatch) return null;
            
            const xauData = xauMatch[1];
            
            // ForexBuying değerini al
            const buyingMatch = xauData.match(/<ForexBuying>([^<]+)<\/ForexBuying>/);
            if (!buyingMatch) return null;
            
            // TCMB'den gelen değer ons altın fiyatı (TRY cinsinden)
            const onsAltinTry = parseFloat(buyingMatch[1].replace(',', '.').replace(/[^\d.]/g, ''));
            
            if (isNaN(onsAltinTry) || onsAltinTry === 0) return null;
            
            // Ons'tan gram'a çevir (1 ons = 31.1035 gram)
            const gramAltinTry = onsAltinTry / 31.1035;
            
            return {
                gram: gramAltinTry,
                ceyrek: gramAltinTry * 1.750 * 1.03,
                yarim: gramAltinTry * 3.500 * 1.03,
                tam: gramAltinTry * 7.216 * 1.05,
                cumhuriyet: gramAltinTry * 7.216 * 1.05,
                resat: gramAltinTry * 7.200 * 1.08,
                bilezik22: gramAltinTry * (22/24),
                bilezik18: gramAltinTry * (18/24),
                bilezik14: gramAltinTry * (14/24),
                _changes: {}
            };
        }
    } catch (e) {
        console.warn('⚠️ TCMB API hatası:', e.message);
    }
    return null;
}

// anlikaltinfiyati.com'dan altın fiyatlarını çek
async function scrapeAnlikAltinFiyati() {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000);
        
        const response = await fetch('https://www.anlikaltinfiyati.com/', {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) return null;
        
        const html = await response.text();
        
        // HTML'den fiyatları parse et
        // Daha iyi regex pattern'ler kullanılabilir
        const gramMatch = html.match(/Gram[^>]*Altın[^>]*>[\s\S]{0,500}?(\d{3,5}[.,]\d{2}|\d{3,5})/i);
        const ceyrekMatch = html.match(/Çeyrek[^>]*Altın[^>]*>[\s\S]{0,500}?(\d{3,5}[.,]\d{2}|\d{3,5})/i);
        const tamMatch = html.match(/(Tam|Ata)[^>]*Altın[^>]*>[\s\S]{0,500}?(\d{3,5}[.,]\d{2}|\d{3,5})/i);
        
        const parsePrice = (match) => {
            if (!match) return 0;
            const price = match[1] || match[2];
            return parseFloat(price.replace(',', '.').replace(/[^\d.]/g, '')) || 0;
        };
        
        const gram = parsePrice(gramMatch);
        const ceyrek = parsePrice(ceyrekMatch);
        const tam = parsePrice(tamMatch);
        
        if (gram === 0 && ceyrek === 0 && tam === 0) return null;
        
        return {
            gram: gram || 0,
            ceyrek: ceyrek || (gram * 1.750 * 1.03),
            yarim: (gram * 3.500 * 1.03) || 0,
            tam: tam || (gram * 7.216 * 1.05),
            cumhuriyet: (gram * 7.216 * 1.05) || 0,
            resat: (gram * 7.200 * 1.08) || 0,
            bilezik22: (gram * (22/24)) || 0,
            bilezik18: (gram * (18/24)) || 0,
            bilezik14: (gram * (14/24)) || 0,
            _changes: {}
        };
    } catch (e) {
        console.error('anlikaltinfiyati.com scraping hatası:', e);
        return null;
    }
}

// altin.doviz.com'dan altın fiyatlarını çek
async function scrapeDovizCom() {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000);
        
        const response = await fetch('https://altin.doviz.com/', {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) return null;
        
        const html = await response.text();
        
        // doviz.com HTML yapısına göre parse et
        const gramMatch = html.match(/gram-altin[^>]*>[\s\S]{0,500}?(\d{3,5}[.,]\d{2}|\d{3,5})/i);
        const ceyrekMatch = html.match(/ceyrek-altin[^>]*>[\s\S]{0,500}?(\d{3,5}[.,]\d{2}|\d{3,5})/i);
        const tamMatch = html.match(/(tam|ata)-altin[^>]*>[\s\S]{0,500}?(\d{3,5}[.,]\d{2}|\d{3,5})/i);
        
        const parsePrice = (match) => {
            if (!match) return 0;
            const price = match[1] || match[2];
            return parseFloat(price.replace(',', '.').replace(/[^\d.]/g, '')) || 0;
        };
        
        const gram = parsePrice(gramMatch);
        const ceyrek = parsePrice(ceyrekMatch);
        const tam = parsePrice(tamMatch);
        
        if (gram === 0 && ceyrek === 0 && tam === 0) return null;
        
        return {
            gram: gram || 0,
            ceyrek: ceyrek || (gram * 1.750 * 1.03),
            yarim: (gram * 3.500 * 1.03) || 0,
            tam: tam || (gram * 7.216 * 1.05),
            cumhuriyet: (gram * 7.216 * 1.05) || 0,
            resat: (gram * 7.200 * 1.08) || 0,
            bilezik22: (gram * (22/24)) || 0,
            bilezik18: (gram * (18/24)) || 0,
            bilezik14: (gram * (14/24)) || 0,
            _changes: {}
        };
    } catch (e) {
        console.error('doviz.com scraping hatası:', e);
        return null;
    }
}
