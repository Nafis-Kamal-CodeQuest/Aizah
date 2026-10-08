/* =============================================================
   AIZAH FMCG - motion.js  (Phase 1)
   Depends on: GSAP 3.12.5, ScrollTrigger, Lenis 1.1.13
   ============================================================= */

(function () {
  'use strict';

  var html = document.documentElement;

  /* ----------------------------------------------------------
     RUNTIME CHECKS — done here, not via inline head script,
     because synchronous CDN scripts in <head> can cause the
     browser to execute end-of-body scripts before the inline
     head script has run (readyState: loading).
  ---------------------------------------------------------- */

  // 1. Bail if prefers-reduced-motion
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    return;
  }

  // 2. Bail if required libs missing
  if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined' || typeof Lenis === 'undefined') {
    console.warn('[AizaahMotion] BAIL: missing libs — gsap=' + typeof gsap + ' ST=' + typeof ScrollTrigger + ' Lenis=' + typeof Lenis);
    return;
  }

  // 3. Mark <html> so CSS animation states activate
  html.setAttribute('data-motion', '1');

  /* ----------------------------------------------------------
     HELPERS
  ---------------------------------------------------------- */
  var $ = function (sel, ctx) { return (ctx || document).querySelector(sel); };
  var $$ = function (sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); };

  /* ----------------------------------------------------------
     SCROLL PROGRESS BAR
     A fixed 3-px bar at the very top, scrubbed by GSAP.
  ---------------------------------------------------------- */
  function initScrollProgress() {
    var bar = document.getElementById('scroll-progress');
    if (!bar) return;

    gsap.to(bar, {
      scaleX: 1,
      ease: 'none',
      scrollTrigger: {
        trigger: document.documentElement,
        start: 'top top',
        end: 'bottom bottom',
        scrub: true,
      },
    });
  }

  /* ----------------------------------------------------------
     LENIS SMOOTH SCROLL
     - Desktop only (touch stays native)
     - Synced with GSAP ticker
     - Exposed on window.AizaahMotion.lock / unlock
  ---------------------------------------------------------- */
  var lenis = null;

  function initLenis() {
    lenis = new Lenis({
      lerp:            0.12,
      smoothWheel:     true,
      syncTouch:       false,
      wheelMultiplier: 1,
      orientation:     'vertical',
      gestureOrientation: 'vertical',
      infinite:        false,
    });

    // Sync Lenis with GSAP ticker
    gsap.ticker.add(function (time) {
      lenis.raf(time * 1000);
    });
    gsap.ticker.lagSmoothing(0);

    // Sync ScrollTrigger with Lenis scroll events
    lenis.on('scroll', ScrollTrigger.update);

    // Route all in-page #hash links through Lenis
    var NAVBAR_HEIGHT = 80; // px offset for sticky navbar
    document.addEventListener('click', function (e) {
      var anchor = e.target.closest('a[href^="#"]');
      if (!anchor) return;
      var hash = anchor.getAttribute('href');
      if (hash === '#' || hash.length < 2) return;
      var target = document.querySelector(hash);
      if (!target) return;
      e.preventDefault();
      lenis.scrollTo(target, { offset: -NAVBAR_HEIGHT, duration: 1.1 });
    });
  }

  /* ----------------------------------------------------------
     PUBLIC API: window.AizaahMotion
     lock()   — stop Lenis (call on modal/menu open)
     unlock() — restart Lenis (call on modal/menu close)
  ---------------------------------------------------------- */
  window.AizaahMotion = {
    lock: function () {
      if (lenis) lenis.stop();
    },
    unlock: function () {
      if (lenis) lenis.start();
    },
  };

  /* ----------------------------------------------------------
     PRELOADER
     - Slate-950 overlay with brand wordmark letter stagger
     - cyan/amber progress line
     - Curtain-lift reveal into hero
     - Once per session (sessionStorage)
     - Min 0.9 s, hard cap 2.2 s
  ---------------------------------------------------------- */
  function initPreloader(onDone) {
    var el = document.getElementById('preloader');
    if (!el) { onDone(); return; }

    // Check session — skip if already shown
    if (sessionStorage.getItem('aizah_preloader_shown')) {
      el.style.display = 'none';
      onDone();
      return;
    }

    var letters = $$('.pre-letter', el);
    var tagline = document.getElementById('preloader-tagline');
    var bar     = document.getElementById('preloader-bar');
    var startTime = performance.now();
    var MIN_DURATION = 900;   // ms
    var MAX_DURATION = 2200;  // ms

    function finish() {
      sessionStorage.setItem('aizah_preloader_shown', '1');
      el.classList.add('done', 'curtain-lift');
      // After curtain animation completes, hide the element
      setTimeout(function () {
        el.style.display = 'none';
        onDone();
      }, 780);
    }

    // Hard cap: force finish at MAX_DURATION regardless of load state
    var hardCapTimer = setTimeout(function () {
      finish();
    }, MAX_DURATION);

    // Letter stagger reveal
    var tl = gsap.timeline({
      onComplete: function () {
        var elapsed = performance.now() - startTime;
        var remaining = Math.max(0, MIN_DURATION - elapsed);
        setTimeout(function () {
          clearTimeout(hardCapTimer);
          finish();
        }, remaining);
      }
    });

    tl.to(letters, {
      clipPath: 'inset(0 0 0% 0)',
      duration: 0.55,
      stagger: 0.06,
      ease: 'power3.out',
    });

    tl.to(tagline, {
      opacity: 1,
      y: 0,
      duration: 0.4,
      ease: 'power2.out',
    }, '-=0.15');

    // Progress bar animation — runs in parallel, completes at ~0.9 s
    gsap.to(bar, {
      width: '100%',
      duration: 0.85,
      ease: 'power1.inOut',
    });

    // Kick off hero intro AFTER curtain lifts (called by onDone callback)
  }

  /* ----------------------------------------------------------
     NAVBAR
     - Hides on scroll down (after 120 px)
     - Returns on scroll up
     - .scrolled state for blur/compact
     - .force-show when mobile menu is open
  ---------------------------------------------------------- */
  function initNavbar() {
    var navbar    = document.getElementById('navbar');
    if (!navbar) return;

    var THRESHOLD = 120;
    // Track state to avoid unnecessary class writes
    var state = { scrolled: false, hidden: false };

    // Drive from Lenis scroll event — no window.scrollY reads, no layout reads
    lenis.on('scroll', function (e) {
      var y   = e.scroll;
      var dir = e.direction; // +1 = down, -1 = up

      var wantScrolled = (y > 30);
      var wantHidden   = (y > THRESHOLD && dir > 0);
      var wantVisible  = (dir < 0 || y <= THRESHOLD);

      if (wantScrolled !== state.scrolled) {
        state.scrolled = wantScrolled;
        if (wantScrolled) {
          navbar.classList.add('scrolled');
        } else {
          navbar.classList.remove('scrolled', 'hide-nav');
          state.hidden = false;
        }
      }

      if (wantHidden && !state.hidden && !navbar.classList.contains('force-show')) {
        state.hidden = true;
        navbar.classList.add('hide-nav');
      } else if (wantVisible && state.hidden) {
        state.hidden = false;
        navbar.classList.remove('hide-nav');
      }
    });

    // Keep navbar visible while mobile menu is open
    var menuToggle = document.getElementById('menuToggle');
    var menuClose  = document.getElementById('menuClose');
    var backdrop   = document.getElementById('menuBackdrop');
    var mobileMenu = document.getElementById('mobileMenu');

    function forceShowNav() { navbar.classList.add('force-show'); }
    function releaseNav()   { navbar.classList.remove('force-show'); }

    if (menuToggle) menuToggle.addEventListener('click', forceShowNav);
    if (menuClose)  menuClose.addEventListener('click', releaseNav);
    if (backdrop)   backdrop.addEventListener('click', releaseNav);

    // Mobile link stagger on menu open
    var menuObs = new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        if (m.type === 'attributes' && m.attributeName === 'class') {
          var hidden = mobileMenu.classList.contains('hidden');
          if (!hidden) {
            mobileMenu.classList.add('menu-open');
            var links = $$('.mobile-link', mobileMenu);
            links.forEach(function (link, i) {
              link.style.transitionDelay = (i * 45) + 'ms';
            });
            forceShowNav();
          } else {
            mobileMenu.classList.remove('menu-open');
            var links = $$('.mobile-link', mobileMenu);
            links.forEach(function (link) {
              link.style.transitionDelay = '0ms';
            });
            releaseNav();
          }
        }
      });
    });
    if (mobileMenu) {
      menuObs.observe(mobileMenu, { attributes: true });
    }
  }

  /* ----------------------------------------------------------
     HERO — clip-path wipe transition
     Hooks into the Carousel._onSlideChange no-op.
     Also: Ken Burns (via CSS), ScrollTrigger parallax,
     Magnetic CTA, word-mask headline reveal.
  ---------------------------------------------------------- */

  // Word-split helper: wraps each word in a .hero-word span
  // while preserving an aria-label on the parent for screen readers.
  function splitWords(el) {
    if (!el) return [];
    var text = el.textContent.trim();
    el.setAttribute('aria-label', text);
    el.innerHTML = text.split(/\s+/).map(function (word) {
      return '<span class="hero-word" aria-hidden="true">' + word + '\u00a0</span>';
    }).join('');
    return $$('.hero-word', el);
  }

  // Animate the headline/subtitle/CTA of a slide into view
  function animateSlideContent(slideEl) {
    if (!slideEl) return;
    var h1       = slideEl.querySelector('h1');
    var subtitle = slideEl.querySelector('p');
    var ctaWrap  = slideEl.querySelector('.flex.flex-wrap.gap-3');

    var words = h1 ? splitWords(h1) : [];

    var tl = gsap.timeline({
      defaults: { ease: 'power3.out' },
      onStart: function () {
        // Set will-change only while animating
        words.forEach(function (w) { w.style.willChange = 'clip-path, transform'; });
      },
      onComplete: function () {
        words.forEach(function (w) { w.style.willChange = ''; });
      },
    });

    if (words.length) {
      tl.fromTo(words,
        { clipPath: 'inset(0 0 100% 0)', y: 12 },
        { clipPath: 'inset(0 0 0% 0)', y: 0, duration: 0.6, stagger: 0.04 },
        0
      );
    }

    if (subtitle) {
      tl.fromTo(subtitle,
        { opacity: 0, y: 14 },
        { opacity: 1, y: 0, duration: 0.55 },
        words.length ? 0.18 : 0
      );
    }

    if (ctaWrap) {
      tl.fromTo(ctaWrap,
        { opacity: 0, y: 16 },
        { opacity: 1, y: 0, duration: 0.5 },
        words.length ? 0.3 : 0.1
      );
    }
  }

  // Clip-path wipe slide transition (~0.9 s, cubic easing)
  function wipeTransition(prevEl, nextEl, onComplete) {
    if (!nextEl) { if (onComplete) onComplete(); return; }

    // nextEl already has .active (set by Carousel.goTo).
    // prevEl already had .active removed. We only manage zIndex and clip-path.
    gsap.set(nextEl, { zIndex: 11, opacity: 1, clipPath: 'inset(0 100% 0 0)' });
    if (prevEl) gsap.set(prevEl, { zIndex: 10, opacity: 1 });

    gsap.to(nextEl, {
      clipPath: 'inset(0 0% 0 0)',
      duration: 0.9,
      ease: 'power3.inOut',
      onComplete: function () {
        // Clear GSAP inline styles so CSS takes back control
        if (prevEl) gsap.set(prevEl, { clearProps: 'zIndex,opacity,clipPath' });
        gsap.set(nextEl, { clearProps: 'zIndex,clipPath' });
        if (onComplete) onComplete();
      },
    });
  }

  // Hero scroll parallax — disabled on coarse-pointer (touch/mobile) devices
  function initHeroParallax() {
    // Skip on touch/mobile — parallax costs paint without benefit on small screens
    if (window.matchMedia('(pointer: coarse)').matches) return;

    var heroSection  = document.getElementById('home');
    var contentWrap  = heroSection ? heroSection.querySelector('.relative.h-full') : null;
    if (!heroSection || !contentWrap) return;

    gsap.to(contentWrap, {
      y: 80,
      opacity: 0.4,
      scale: 0.97,
      ease: 'none',
      scrollTrigger: {
        trigger: heroSection,
        start: 'top top',
        end: 'bottom top',
        scrub: true,
        onToggle: function (self) {
          // Set will-change only while scrub is active (hero in viewport)
          contentWrap.style.willChange = self.isActive ? 'transform, opacity' : '';
        },
      },
    });
  }

  // Magnetic CTA (desktop pointer:fine only)
  // Uses event delegation so it works for CTAs in all slides (rendered dynamically).
  function initMagneticCTA() {
    var canHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    if (!canHover) return;

    var heroSection = document.getElementById('home');
    if (!heroSection) return;

    var STRENGTH = 0.35;
    var activeCta = null;
    var quickX = null;
    var quickY = null;
    var cachedRect = null;

    // Cache rect on mouseenter so mousemove never calls getBoundingClientRect
    heroSection.addEventListener('mouseenter', function (e) {
      var cta = e.target.closest('.hero-cta-magnetic');
      if (!cta) return;
      activeCta = cta;
      cachedRect = cta.getBoundingClientRect();
      quickX = gsap.quickTo(cta, 'x', { duration: 0.4, ease: 'power2.out' });
      quickY = gsap.quickTo(cta, 'y', { duration: 0.4, ease: 'power2.out' });
    }, true); // capture to catch bubbling from child elements

    heroSection.addEventListener('mousemove', function (e) {
      if (!activeCta || !cachedRect || !quickX || !quickY) return;
      var cta = e.target.closest('.hero-cta-magnetic');
      if (cta !== activeCta) return;
      var cx = cachedRect.left + cachedRect.width  / 2;
      var cy = cachedRect.top  + cachedRect.height / 2;
      quickX((e.clientX - cx) * STRENGTH);
      quickY((e.clientY - cy) * STRENGTH);
    });

    heroSection.addEventListener('mouseleave', function (e) {
      var cta = e.target.closest('.hero-cta-magnetic');
      if (!cta && !activeCta) return;
      var target = cta || activeCta;
      gsap.to(target, { x: 0, y: 0, duration: 0.5, ease: 'elastic.out(1, 0.5)' });
      activeCta = null;
      cachedRect = null;
      quickX = null;
      quickY = null;
    }, true);
  }

  function initHeroAnimations() {
    var heroSection = document.getElementById('home');
    var carousel    = document.getElementById('carousel');
    if (!heroSection || !carousel) return;

    // IntersectionObserver: pause Ken Burns when hero is out of viewport
    var heroIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          heroSection.classList.add('hero-in-view');
        } else {
          heroSection.classList.remove('hero-in-view');
        }
      });
    }, { threshold: 0 });
    heroIO.observe(heroSection);
    // Set initial state
    if (heroSection.getBoundingClientRect().top < window.innerHeight) {
      heroSection.classList.add('hero-in-view');
    }

    // Hook into Carousel._onSlideChange via a CustomEvent
    // The page IIFE's heroCarousel is stored in its internal `state` object.
    // We listen on the carousel container for the custom event we dispatch below.
    carousel.addEventListener('aizah:slidechange', function (e) {
      var prevIdx = e.detail.prev;
      var nextIdx = e.detail.next;
      var slides  = Array.from(carousel.querySelectorAll('.carousel-slide'));
      var prevEl  = slides[prevIdx] || null;
      var nextEl  = slides[nextIdx] || null;

      wipeTransition(prevEl, nextEl, function () {
        animateSlideContent(nextEl);
      });
    });

    // Also animate the initial (first) slide on hero entry
    // fired after preloader done
    carousel.addEventListener('aizah:herointro', function () {
      var firstSlide = carousel.querySelector('.carousel-slide.active');
      if (firstSlide) animateSlideContent(firstSlide);
    });

    initHeroParallax();
    initMagneticCTA();
  }

  /* ----------------------------------------------------------
     STATS BAR — count-up animation
     Reads data-count and data-suffix from the stat number divs.
  ---------------------------------------------------------- */
  function initStatsCountUp() {
    var statItems = $$('[data-count]');
    if (!statItems.length) return;

    statItems.forEach(function (el) {
      var target = parseFloat(el.getAttribute('data-count'));
      var suffix = el.getAttribute('data-suffix') || '';
      var comma  = el.getAttribute('data-comma') === 'true';
      var delay  = parseFloat(el.getAttribute('data-stat-delay') || '0');

      ScrollTrigger.create({
        trigger: el,
        start: 'top 80%',
        once: true,
        onEnter: function () {
          var obj = { val: 0 };
          gsap.to(obj, {
            val: target,
            duration: 1.6,
            delay: delay,
            ease: 'power2.out',
            onUpdate: function () {
              var v       = Math.round(obj.val);
              var display = comma ? v.toLocaleString('en-US') : String(v);
              el.textContent = display + suffix;
            },
            onComplete: function () {
              // Guarantee exact final value
              var v       = Math.round(target);
              var display = comma ? v.toLocaleString('en-US') : String(v);
              el.textContent = display + suffix;
            },
          });
        },
      });
    });
  }

  /* ----------------------------------------------------------
     DATA-REVEAL UTILITY
     Generic fade-up for any [data-reveal] element.
     Optional data-reveal-delay (seconds).
  ---------------------------------------------------------- */
  function initDataReveal() {
    var els = $$('[data-reveal]');
    if (!els.length) return;

    els.forEach(function (el) {
      var delay = parseFloat(el.getAttribute('data-reveal-delay') || '0');

      ScrollTrigger.create({
        trigger: el,
        start: 'top 88%',
        once: true,
        onEnter: function () {
          el.style.willChange = 'opacity, transform';
          gsap.to(el, {
            opacity: 1,
            y: 0,
            duration: 0.65,
            delay: delay,
            ease: 'power2.out',
            onComplete: function () {
              el.style.willChange = '';
            },
          });
        },
      });
    });
  }

  /* ----------------------------------------------------------
     SCROLLTRIGGER REFRESH
     The page IIFE (non-deferred) runs before motion.js (deferred),
     so by the time we init, content is already rendered.
     We refresh immediately and also listen for future re-renders.
  ---------------------------------------------------------- */
  function scheduleRefresh() {
    // Content already rendered by IIFE — do an initial refresh
    // Use rAF to let layout settle first
    requestAnimationFrame(function () {
      ScrollTrigger.refresh();
    });

    // Listen for future re-renders (filter changes, etc.)
    document.addEventListener('aizah:contentrendered', function () {
      requestAnimationFrame(function () {
        ScrollTrigger.refresh();
      });
    });

    // Final refresh after all images load
    window.addEventListener('load', function () {
      ScrollTrigger.refresh();
    });
  }

  /* ----------------------------------------------------------
     PATCH EXISTING PAGE IIFE HOOKS
     We need to:
     1. Dispatch 'aizah:slidechange' CustomEvent from Carousel._onSlideChange
     2. Dispatch 'aizah:contentrendered' after renderProducts + initOffersCarousel
     3. Patch openModal / closeModal to call AizaahMotion.lock / unlock
     4. Patch openMenu / closeMenu to call AizaahMotion.lock / unlock

     We do this by observing the DOM rather than monkey-patching the IIFE
     (which is enclosed and hard to reach), using CustomEvents where possible.
     The Carousel hook is patched via the window.AizaahMotion bridge by
     waiting for the heroCarousel to appear on window.aizahState (if exposed),
     or by intercepting via a MutationObserver on #carousel's active class.
  ---------------------------------------------------------- */

  // Patch: watch for hero carousel slide transitions by observing
  // .carousel-slide.active class changes on #carousel children.
  function patchCarouselTransition() {
    var carousel = document.getElementById('carousel');
    if (!carousel) return;

    var prevActive = -1;

    var obs = new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        if (m.type !== 'attributes' || m.attributeName !== 'class') return;
        var target = m.target;
        if (!target.classList.contains('carousel-slide')) return;

        if (target.classList.contains('active')) {
          // Find index
          var slides  = Array.from(carousel.querySelectorAll('.carousel-slide'));
          var nextIdx = slides.indexOf(target);
          if (nextIdx === -1 || nextIdx === prevActive) return;

          // Dispatch custom event so initHeroAnimations can react
          var evt = new CustomEvent('aizah:slidechange', {
            detail: { prev: prevActive, next: nextIdx },
          });
          carousel.dispatchEvent(evt);
          prevActive = nextIdx;
        }
      });
    });

    obs.observe(carousel, { attributes: true, subtree: true, attributeFilter: ['class'] });

    // Track initial active slide index
    var slides = Array.from(carousel.querySelectorAll('.carousel-slide'));
    slides.forEach(function (s, i) {
      if (s.classList.contains('active')) prevActive = i;
    });
  }

  // Patch: watch for modal open/close via body.scroll-lock changes
  // combined with #productModal visibility.
  function patchModalScrollLock() {
    var modal = document.getElementById('productModal');
    if (!modal) return;

    var obs = new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        if (m.type !== 'attributes' || m.attributeName !== 'class') return;
        var hidden = modal.classList.contains('hidden');
        if (!hidden) {
          window.AizaahMotion.lock();
        } else {
          window.AizaahMotion.unlock();
        }
      });
    });

    obs.observe(modal, { attributes: true, attributeFilter: ['class'] });
  }

  // Patch: watch mobile menu for open/close to lock/unlock Lenis
  function patchMobileMenuScrollLock() {
    var mobileMenu = document.getElementById('mobileMenu');
    if (!mobileMenu) return;

    var obs = new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        if (m.type !== 'attributes' || m.attributeName !== 'class') return;
        if (!mobileMenu.classList.contains('hidden')) {
          window.AizaahMotion.lock();
        } else {
          window.AizaahMotion.unlock();
        }
      });
    });

    obs.observe(mobileMenu, { attributes: true, attributeFilter: ['class'] });
  }

  /* ----------------------------------------------------------
     HERO INTRO — fires after preloader curtain lifts
  ---------------------------------------------------------- */
  function fireHeroIntro() {
    var carousel = document.getElementById('carousel');
    if (carousel) {
      carousel.dispatchEvent(new CustomEvent('aizah:herointro'));
    }
  }

  /* ----------------------------------------------------------
     PHASE 2 — SECTION ANIMATIONS
     Offers card stagger, products grid stagger + filter transition,
     About section splits, Contact reveals.
     All gated by [data-motion="1"] via the existing initDataReveal().
     These functions add *additional* GSAP-driven sequences on top
     of the generic [data-reveal] utility.
  ---------------------------------------------------------- */

  /* ── Offers: stagger the carousel cards in after content renders ── */
  function initOffersAnimations() {
    var carousel = document.getElementById('offersCarousel');
    if (!carousel) return;

    function animateCards() {
      var cards = Array.from(carousel.querySelectorAll('.offers-slide'));
      if (!cards.length) return;
      // Stagger active + inactive cards from y=40 opacity=0
      gsap.fromTo(cards,
        { opacity: 0, y: 40 },
        {
          opacity: 1,
          y: 0,
          duration: 0.55,
          stagger: 0.10,
          ease: 'power2.out',
          clearProps: 'transform',
        }
      );
    }

    // Wait for offers to be injected by the IIFE
    var obs = new MutationObserver(function () {
      if (carousel.children.length > 0) {
        obs.disconnect();
        // Small delay so the carousel CSS stacking is stable
        setTimeout(animateCards, 80);
      }
    });
    obs.observe(carousel, { childList: true });
    if (carousel.children.length > 0) animateCards();
  }

  /* ── Products: stagger on first render, crossfade on re-render ── */
  function initProductsAnimations() {
    var grid = document.getElementById('productsGrid');
    if (!grid) return;

    var firstRender = true;

    function animateGrid(cards) {
      if (!cards.length) return;
      if (firstRender) {
        firstRender = false;
        // Full stagger entrance from below
        gsap.fromTo(cards,
          { opacity: 0, y: 32 },
          {
            opacity: 1,
            y: 0,
            duration: 0.45,
            stagger: 0.06,
            ease: 'power2.out',
            clearProps: 'transform,opacity',
          }
        );
      } else {
        // Subsequent renders (filter / search): quick fade in
        gsap.fromTo(cards,
          { opacity: 0, scale: 0.96 },
          {
            opacity: 1,
            scale: 1,
            duration: 0.30,
            stagger: 0.04,
            ease: 'power2.out',
            clearProps: 'transform,opacity',
          }
        );
      }
    }

    // Watch for grid content changes
    var obs = new MutationObserver(function () {
      var cards = Array.from(grid.querySelectorAll('.product-card'));
      if (cards.length) {
        // Cancel any running tween so stagger doesn't stack
        gsap.killTweensOf(cards);
        animateGrid(cards);
      }
    });
    obs.observe(grid, { childList: true });

    // Animate initial render if cards already present
    var initial = Array.from(grid.querySelectorAll('.product-card'));
    if (initial.length) animateGrid(initial);
  }

  /* ── About: split the h2 headline into words for a mask reveal ── */
  function initAboutAnimations() {
    var aboutSection = document.getElementById('about');
    if (!aboutSection) return;

    var h2 = aboutSection.querySelector('h2');
    if (!h2) return;

    // Re-use the existing splitWords helper
    var words = splitWords(h2);
    if (!words.length) return;

    ScrollTrigger.create({
      trigger: h2,
      start: 'top 85%',
      once: true,
      onEnter: function () {
        words.forEach(function (w) { w.style.willChange = 'clip-path, transform'; });
        gsap.fromTo(words,
          { clipPath: 'inset(0 0 100% 0)', y: 10 },
          {
            clipPath: 'inset(0 0 0% 0)',
            y: 0,
            duration: 0.55,
            stagger: 0.045,
            ease: 'power3.out',
            onComplete: function () {
              words.forEach(function (w) { w.style.willChange = ''; });
            },
          }
        );
      },
    });
  }

  /* ── Footer: simple fade-up for the 4 footer columns ── */
  function initFooterAnimations() {
    var footer = document.querySelector('footer');
    if (!footer) return;

    var cols = Array.from(footer.querySelectorAll('.grid > div'));
    if (!cols.length) return;

    ScrollTrigger.create({
      trigger: footer,
      start: 'top 90%',
      once: true,
      onEnter: function () {
        gsap.fromTo(cols,
          { opacity: 0, y: 24 },
          {
            opacity: 1,
            y: 0,
            duration: 0.5,
            stagger: 0.08,
            ease: 'power2.out',
            clearProps: 'transform,opacity',
          }
        );
      },
    });
  }

  /* ----------------------------------------------------------
     INIT SEQUENCE
  ---------------------------------------------------------- */
  function init() {
    gsap.registerPlugin(ScrollTrigger);

    // 1. Preloader — blocks hero intro until done
    initPreloader(function () {
      // Hero intro after curtain lifts
      fireHeroIntro();
    });

    // 2. Scroll progress bar
    initScrollProgress();

    // 3. Lenis smooth scroll
    initLenis();

    // 4. Navbar behaviour
    initNavbar();

    // 5. Hero animations & wipe transition
    initHeroAnimations();

    // 6. Carousel mutation observer (patch)
    patchCarouselTransition();

    // 7. Stats count-up
    initStatsCountUp();

    // 8. Data-reveal utility (generic fade-up for all [data-reveal] elements)
    initDataReveal();

    // 9. ScrollTrigger refresh hooks
    scheduleRefresh();

    // 10. Patch modal + mobile menu for Lenis lock
    patchModalScrollLock();
    patchMobileMenuScrollLock();

    // 11. Phase 2 section animations
    initOffersAnimations();
    initProductsAnimations();
    initAboutAnimations();
    initFooterAnimations();
  }

  // Run after DOM is ready (script is deferred, so DOM is ready)
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

}());
