const LOGOS = [
  {
    src: 'https://svgl.app/procure.svg',
    alt: 'Procure',
    gradient: 'from-blue-400 to-blue-600',
  },
  {
    src: 'https://svgl.app/shopify.svg',
    alt: 'Shopify',
    gradient: 'from-yellow-300 to-amber-500',
  },
  {
    src: 'https://svgl.app/blender.svg',
    alt: 'Blender',
    gradient: 'from-blue-400 to-sky-600',
  },
  {
    src: 'https://svgl.app/figma.svg',
    alt: 'Figma',
    gradient: 'from-purple-400 to-fuchsia-600',
  },
  {
    src: 'https://svgl.app/spotify.svg',
    alt: 'Spotify',
    gradient: 'from-pink-400 to-red-500',
  },
  {
    src: 'https://svgl.app/lottielab.svg',
    alt: 'Lottielab',
    gradient: 'from-yellow-300 to-lime-500',
  },
  {
    src: 'https://svgl.app/google-cloud.svg',
    alt: 'Google Cloud',
    gradient: 'from-sky-300 to-blue-500',
  },
  {
    src: 'https://svgl.app/bing.svg',
    alt: 'Bing',
    gradient: 'from-cyan-400 to-teal-500',
  },
] as const;

function LogoCard({
  src,
  alt,
  gradient,
}: {
  src: string;
  alt: string;
  gradient: string;
}) {
  return (
    <div className="group relative h-24 w-40 shrink-0 flex items-center justify-center rounded-full bg-white border border-slate-200/60 shadow-sm hover:border-slate-300 transition-all overflow-hidden">
      <div
        className={`absolute inset-0 scale-150 opacity-0 bg-gradient-to-br ${gradient} transition-all duration-500 group-hover:scale-100 group-hover:opacity-100`}
        aria-hidden
      />
      <img
        src={src}
        alt={alt}
        className="relative z-10 h-10 w-10 object-contain transition-all duration-300 group-hover:brightness-0 group-hover:invert"
        loading="lazy"
        decoding="async"
      />
    </div>
  );
}

export function LogoMarquee() {
  const loop = [...LOGOS, ...LOGOS];

  return (
    <div
      className="marquee-scroller mt-10 relative w-full max-w-[1400px] mx-auto overflow-hidden"
      style={{
        maskImage:
          'linear-gradient(to right, transparent, black 8%, black 92%, transparent)',
        WebkitMaskImage:
          'linear-gradient(to right, transparent, black 8%, black 92%, transparent)',
      }}
    >
      <div className="marquee-track flex items-center gap-4 pr-4">
        {loop.map((logo, index) => (
          <LogoCard
            key={`${logo.alt}-${index}`}
            src={logo.src}
            alt={logo.alt}
            gradient={logo.gradient}
          />
        ))}
      </div>
    </div>
  );
}
