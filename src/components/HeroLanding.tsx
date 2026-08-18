import { motion, useReducedMotion } from 'motion/react';
import { ChevronRight } from 'lucide-react';

const HERO_VIDEO =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260505_101331_74f9b798-3f00-4e86-8a01-377aa16ffeaa.mp4';

interface Props {
  onContact?: () => void;
  onProducts?: () => void;
  onDocs?: () => void;
}

export function HeroLanding({ onContact, onProducts, onDocs }: Props) {
  const reduce = useReducedMotion();

  return (
    <section className="relative w-full max-w-[1400px] mx-auto rounded-[48px] bg-white border border-slate-200/50 shadow-[0_40px_100px_-20px_rgba(0,0,0,0.03)] overflow-hidden h-[600px] flex flex-col">
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden select-none">
        <video
          src={HERO_VIDEO}
          autoPlay
          loop
          muted
          playsInline
          className="w-full h-full object-cover scale-105 transition-transform duration-1000"
        />
      </div>

      <motion.div
        className="relative z-20 flex-1 px-8 md:px-16 pt-12 md:pt-16 flex flex-col items-start"
        initial={reduce ? false : { opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      >
        <h1 className="font-display text-[42px] md:text-[56px] font-medium tracking-tight text-[#0a1b33] leading-[1.08] max-w-[14ch]">
          Foundation of the
          <br />
          new digital epoch
        </h1>
        <p className="mt-5 max-w-[42ch] font-sans text-[14px] md:text-[15px] leading-relaxed text-[#64748b]">
          Designing products, powering ecosystems and laying the foundation of a
          decentralized web for enterprises, builders and communities alike.
        </p>
        <motion.button
          type="button"
          onClick={onContact}
          className="mt-8 rounded-full bg-[#0a152d] px-6 py-3 text-[13px] font-semibold text-white"
          whileHover={reduce ? undefined : { scale: 1.04 }}
          whileTap={reduce ? undefined : { scale: 0.98 }}
        >
          Contact Us
        </motion.button>
      </motion.div>

      <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-30">
        <motion.nav
          className="flex items-center bg-white/90 backdrop-blur-2xl px-1.5 py-1.5 rounded-full shadow-[0_12px_40px_rgba(0,0,0,0.08)] border border-slate-200/40"
          initial={reduce ? false : { opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            duration: 0.65,
            delay: 0.22,
            ease: [0.16, 1, 0.3, 1],
          }}
          aria-label="Primary"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-100 bg-white shadow-sm text-[#0a1b33]">
            ✦
          </div>
          <button
            type="button"
            onClick={onProducts}
            className="px-4 py-2 text-[12px] font-semibold text-slate-500 hover:text-[#0a1b33] transition-colors"
          >
            Products
          </button>
          <button
            type="button"
            onClick={onDocs}
            className="px-4 py-2 text-[12px] font-semibold text-slate-500 hover:text-[#0a1b33] transition-colors"
          >
            Docs
          </button>
          <button
            type="button"
            onClick={onContact}
            className="ml-1 inline-flex items-center gap-1 bg-white px-5 py-2 rounded-full text-[12px] font-semibold text-[#0a1b33] border border-slate-200/60 shadow-sm hover:border-slate-300 transition-all"
          >
            Get in touch
            <ChevronRight className="h-3.5 w-3.5" strokeWidth={2} />
          </button>
        </motion.nav>
      </div>
    </section>
  );
}
