// Supabase Edge Function: sinir-bekleme
// Google Maps Directions API ile sınır kapılarındaki anlık trafik süresi ölçer.
// Çağrı: POST /functions/v1/sinir-bekleme
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const GOOGLE_KEY = Deno.env.get('GOOGLE_MAPS_API_KEY')!;

// Her kapı için: Turkish side origin (yaklaşık 8 km önce) → diğer taraf destination (5 km sonra)
// Baseline: trafik yokken beklenen normal seyahat süresi (saniye)
const KAPILER = [
  {
    slug: 'kapikule',
    isim: 'Kapıkule',
    origin: '41.7200,26.6400',    // E80 Edirne yakını, TR tarafı
    dest:   '41.7550,26.4900',    // Bulgarian A4, BG tarafı
    baseline: 660,                 // ~11 dk normal süre
  },
  {
    slug: 'hamzabeyli',
    isim: 'Hamzabeyli',
    origin: '41.7000,26.7200',    // TR D550 yaklaşımı
    dest:   '41.7300,26.5500',    // BG tarafı Lesovo sonrası
    baseline: 600,
  },
  {
    slug: 'ipsala',
    isim: 'İpsala',
    origin: '40.9200,26.4600',    // TR D110 İpsala öncesi
    dest:   '40.9150,26.2800',    // GR Kipi sonrası
    baseline: 600,
  },
  {
    slug: 'derekoy',
    isim: 'Dereköy',
    origin: '41.9600,27.5100',    // TR tarafı yaklaşım
    dest:   '42.0050,27.3600',    // BG Malko Tarnovo sonrası
    baseline: 720,
  },
  {
    slug: 'pazarkule',
    isim: 'Pazarkule',
    origin: '41.6950,26.4200',    // TR Edirne güneyi
    dest:   '41.7450,26.2700',    // GR Kastanies sonrası
    baseline: 660,
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
    // duration_in_traffic varsa kullan, yoksa duration
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

  const sonuclar: Array<{ slug: string; wait: number | null; travel: number | null }> = [];

  for (const kapi of KAPILER) {
    const travel = await googleSureCek(kapi.origin, kapi.dest);
    const wait = travel !== null ? Math.max(0, Math.round((travel - kapi.baseline) / 60)) : null;
    sonuclar.push({ slug: kapi.slug, wait, travel });

    // Upsert: her kapı için tek satır, her çağrıda güncellenir
    await sb.from('border_wait_times').upsert({
      gate_slug:    kapi.slug,
      gate_name:    kapi.isim,
      wait_mins:    wait,
      travel_secs:  travel,
      checked_at:   new Date().toISOString(),
    }, { onConflict: 'gate_slug' });

    // Google rate limit için kısa bekleme
    await new Promise(r => setTimeout(r, 300));
  }

  return new Response(JSON.stringify({ ok: true, kapiler: sonuclar }), {
    headers: { 'Content-Type': 'application/json' },
  });
});
