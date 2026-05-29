// Supabase Edge Function: sinir-bekleme
// Google Maps Directions API ile sınır kapılarındaki anlık trafik süresi ölçer.
// Her kapı için hem giriş (Avrupa→TR) hem çıkış (TR→Avrupa) yönü ayrı ölçülür.
// Çağrı: POST /functions/v1/sinir-bekleme
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const GOOGLE_KEY = Deno.env.get('GOOGLE_MAPS_API_KEY')!;

// Her kapı için TR tarafı ve Avrupa tarafı koordinatları
// cikis: TR→Avrupa (gurbetçi tatilden dönerken Türkiye'den çıkış)
// giris: Avrupa→TR (gurbetçi tatile giderken Türkiye'ye giriş)
// Baseline: trafik yokken beklenen normal seyahat süresi (saniye)
const KAPILER = [
  {
    slug: 'kapikule',
    isim: 'Kapıkule',
    cikis_origin:   '41.7200,26.6400',  // E80 Edirne yakını, TR tarafı
    cikis_dest:     '41.7550,26.4900',  // Bulgarian A4, BG tarafı
    cikis_baseline: 660,
    giris_origin:   '41.7550,26.4900',  // Bulgarian A4, BG tarafı
    giris_dest:     '41.7200,26.6400',  // E80 Edirne yakını, TR tarafı
    giris_baseline: 660,
  },
  {
    slug: 'hamzabeyli',
    isim: 'Hamzabeyli',
    cikis_origin:   '41.7000,26.7200',  // TR D550 yaklaşımı
    cikis_dest:     '41.7300,26.5500',  // BG tarafı Lesovo sonrası
    cikis_baseline: 600,
    giris_origin:   '41.7300,26.5500',
    giris_dest:     '41.7000,26.7200',
    giris_baseline: 600,
  },
  {
    slug: 'ipsala',
    isim: 'İpsala',
    cikis_origin:   '40.9200,26.4600',  // TR D110 İpsala öncesi
    cikis_dest:     '40.9150,26.2800',  // GR Kipi sonrası
    cikis_baseline: 600,
    giris_origin:   '40.9150,26.2800',
    giris_dest:     '40.9200,26.4600',
    giris_baseline: 600,
  },
  {
    slug: 'derekoy',
    isim: 'Dereköy',
    cikis_origin:   '41.9600,27.5100',  // TR tarafı yaklaşım
    cikis_dest:     '42.0050,27.3600',  // BG Malko Tarnovo sonrası
    cikis_baseline: 720,
    giris_origin:   '42.0050,27.3600',
    giris_dest:     '41.9600,27.5100',
    giris_baseline: 720,
  },
  {
    slug: 'pazarkule',
    isim: 'Pazarkule',
    cikis_origin:   '41.6950,26.4200',  // TR Edirne güneyi
    cikis_dest:     '41.7450,26.2700',  // GR Kastanies sonrası
    cikis_baseline: 660,
    giris_origin:   '41.7450,26.2700',
    giris_dest:     '41.6950,26.4200',
    giris_baseline: 660,
  },
];

async function googleSureCek(origin: string, dest: string): Promise<number | null> {
  const departure = Math.floor(Date.now() / 1000);
  const url = `https://maps.googleapis.com/maps/api/directions/json` +
    `?origin=${origin}&destination=${dest}` +
    `&departure_time=${departure}&traffic_model=best_guess&key=${GOOGLE_KEY}`;

  try {
    const r = await fetch(url);
    const data = await r.json();
    if (data.status !== 'OK') {
      console.warn(`Google API hata [${data.status}]:`, data.error_message || '');
      return null;
    }
    const leg = data.routes?.[0]?.legs?.[0];
    return leg?.duration_in_traffic?.value ?? leg?.duration?.value ?? null;
  } catch (e) {
    console.error('Fetch hata:', e);
    return null;
  }
}

Deno.serve(async (req) => {
  const sb = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  );

  const sonuclar: Array<{
    slug: string;
    cikis_wait: number | null;
    giris_wait: number | null;
  }> = [];

  for (const kapi of KAPILER) {
    // Çıkış: TR → Avrupa
    const cikisTravel = await googleSureCek(kapi.cikis_origin, kapi.cikis_dest);
    const cikisWait = cikisTravel !== null
      ? Math.max(0, Math.round((cikisTravel - kapi.cikis_baseline) / 60))
      : null;

    await new Promise(r => setTimeout(r, 300));

    // Giriş: Avrupa → TR
    const girisTravel = await googleSureCek(kapi.giris_origin, kapi.giris_dest);
    const girisWait = girisTravel !== null
      ? Math.max(0, Math.round((girisTravel - kapi.giris_baseline) / 60))
      : null;

    sonuclar.push({ slug: kapi.slug, cikis_wait: cikisWait, giris_wait: girisWait });

    // Çıkış upsert
    await sb.from('border_wait_times').upsert({
      gate_slug:   kapi.slug,
      gate_name:   kapi.isim,
      yon:         'cikis',
      wait_mins:   cikisWait,
      travel_secs: cikisTravel,
      checked_at:  new Date().toISOString(),
    }, { onConflict: 'gate_slug,yon' });

    // Giriş upsert
    await sb.from('border_wait_times').upsert({
      gate_slug:   kapi.slug,
      gate_name:   kapi.isim,
      yon:         'giris',
      wait_mins:   girisWait,
      travel_secs: girisTravel,
      checked_at:  new Date().toISOString(),
    }, { onConflict: 'gate_slug,yon' });

    // Google rate limit için bekleme
    await new Promise(r => setTimeout(r, 300));
  }

  return new Response(JSON.stringify({ ok: true, kapiler: sonuclar }), {
    headers: { 'Content-Type': 'application/json' },
  });
});
