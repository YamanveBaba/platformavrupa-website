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
    // Çıkış: TR E80'de Edirne'den sınıra yaklaşma (~5km TR tarafı)
    cikis_origin:   '41.7140,26.6250',
    cikis_dest:     '41.7310,26.5810',
    cikis_baseline: 300,
    // Giriş: BG A4'te Bulgaristan tarafından sınıra yaklaşma (~5km BG tarafı)
    giris_origin:   '41.7600,26.4870',
    giris_dest:     '41.7440,26.5480',
    giris_baseline: 300,
  },
  {
    slug: 'hamzabeyli',
    isim: 'Hamzabeyli',
    // Çıkış: TR D550'de sınıra yaklaşma
    cikis_origin:   '41.7050,26.6780',
    cikis_dest:     '41.7180,26.6420',
    cikis_baseline: 240,
    // Giriş: BG tarafı Svilengrad'dan sınıra yaklaşma
    giris_origin:   '41.7380,26.5700',
    giris_dest:     '41.7250,26.6050',
    giris_baseline: 240,
  },
  {
    slug: 'ipsala',
    isim: 'İpsala',
    // Çıkış: TR D110 (E90) sınıra yaklaşma
    cikis_origin:   '40.8970,26.4580',
    cikis_dest:     '40.9100,26.3980',
    cikis_baseline: 300,
    // Giriş: GR tarafı Kipi'den sınıra yaklaşma
    giris_origin:   '40.9250,26.3050',
    giris_dest:     '40.9130,26.3680',
    giris_baseline: 300,
  },
  {
    slug: 'derekoy',
    isim: 'Dereköy',
    // Çıkış: TR D100 Kırklareli'den sınıra yaklaşma
    cikis_origin:   '41.9480,27.4920',
    cikis_dest:     '41.9680,27.4590',
    cikis_baseline: 360,
    // Giriş: BG Malko Tarnovo tarafından yaklaşma
    giris_origin:   '42.0100,27.3750',
    giris_dest:     '41.9870,27.4250',
    giris_baseline: 360,
  },
  {
    slug: 'pazarkule',
    isim: 'Pazarkule',
    // Çıkış: TR D060 Edirne'den sınıra yaklaşma
    cikis_origin:   '41.6840,26.4140',
    cikis_dest:     '41.7010,26.3630',
    cikis_baseline: 300,
    // Giriş: GR Kastanies tarafından yaklaşma
    giris_origin:   '41.7420,26.2700',
    giris_dest:     '41.7160,26.3340',
    giris_baseline: 300,
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
