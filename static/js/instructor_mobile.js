(function(){
  // Robust sidebar toggle wiring for instructor mobile
  function log(){ try{ console.log.apply(console, arguments); console.debug.apply(console, arguments); }catch(e){} }

  function ensureHandlers(){
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    // look for a variety of possible toggle selectors (mobile-specific and legacy)
    const toggles = Array.from(document.querySelectorAll('.mobile-sidebar-toggle, .sidebar-toggle, [data-toggle="sidebar"], button[onclick*="toggleSidebar"], a[onclick*="toggleSidebar"]'));

    function openSidebar(){
      if(!sidebar) return;
      // remove tailwind class that hides the sidebar and mark open
      sidebar.classList.remove('-translate-x-full');
      sidebar.classList.add('open');
      // ensure transform style is clear so CSS (and mutation observer) can handle transitions
      sidebar.style.transform = '';
      if(overlay){ overlay.classList.remove('hidden'); overlay.style.display='block'; overlay.style.pointerEvents='auto'; overlay.style.opacity='1'; }
    }
    function closeSidebar(){
      if(!sidebar) return;
      sidebar.classList.remove('open');
      // add tailwind class that moves sidebar off-screen
      sidebar.classList.add('-translate-x-full');
      // clear any inline transform to allow tailwind translate to take effect
      sidebar.style.transform = '';
      if(overlay){ overlay.classList.add('hidden'); overlay.style.display='none'; overlay.style.pointerEvents='none'; overlay.style.opacity='0'; }
    }
    let _lastToggleAt = 0;
    function toggle(){
      if(!sidebar) return;
      const now = Date.now();
      // debounce rapid/double calls (prevents inline onclick + event listener from canceling each other)
      if(now - _lastToggleAt < 250) return;
      _lastToggleAt = now;
      if(sidebar.classList.contains('open')){ closeSidebar(); log('toggleSidebar clicked, opened=false'); }
      else { openSidebar(); log('toggleSidebar clicked, opened=true'); }
    }

    // attach to existing toggles
    function attachToToggles(){
      toggles.forEach(btn=>{
      // ensure button is visible on mobile even if some CSS hides it
      try{
        const cs = window.getComputedStyle(btn);
        if(cs && (cs.display === 'none' || cs.visibility === 'hidden')){
          btn.style.display = 'inline-flex';
        }
      }catch(e){ }

      // position and stacking to ensure it's clickable on mobile
      btn.style.position = btn.style.position || 'relative';
      btn.style.zIndex = btn.style.zIndex || '200000';
      btn.style.pointerEvents = btn.style.pointerEvents || 'auto';

      // remove any previous handlers we control, then attach both touch and click handlers
      btn.removeEventListener('click', toggle);
      btn.removeEventListener('touchstart', toggle);

      btn.addEventListener('click', function(e){ e.preventDefault(); toggle(); log('mobile toggle clicked (click)'); });
      btn.addEventListener('touchstart', function(e){ e.preventDefault(); toggle(); log('mobile toggle clicked (touchstart)'); }, {passive:false});
      });
    }
    attachToToggles();
    // attach to overlay
    if(overlay){ overlay.addEventListener('click', function(e){ e.preventDefault(); closeSidebar(); }); }

    // Close sidebar when clicking any link or button inside it (mobile only)
    function attachCloseOnLinks(){
      if(!sidebar) return;
      const sidebarLinks = Array.from(sidebar.querySelectorAll('a, button'));
      sidebarLinks.forEach(link=>{
        // remove previous to avoid duplicate handlers
        link.removeEventListener('click', closeSidebarOnClick);
        link.addEventListener('click', closeSidebarOnClick);
      });
    }
    function closeSidebarOnClick(e){
      // if clicking inside sidebar and on mobile, close it
      if(window.innerWidth < 1024){ closeSidebar(); }
    }

    // attach close handlers now and also attempt again shortly (for dynamic content)
    attachCloseOnLinks();
    setTimeout(attachCloseOnLinks, 500);

    // If no visible toggle, create a permanent fallback button (immediately so user always has a control)
    function ensureFallback(){
      const visibleToggle = toggles.find(t=>{ try{ const r=t.getBoundingClientRect(); return r.width>0 && r.height>0; }catch(e){ return false; } });
      if(!visibleToggle){
        if(!document.getElementById('mobile-sidebar-fallback')){
          const fb = document.createElement('button');
          fb.id='mobile-sidebar-fallback';
          fb.setAttribute('aria-label','Open menu');
          fb.innerHTML = '<i class="fas fa-bars"></i>';
          fb.style.position='fixed';
          fb.style.left='10px';
          fb.style.top='10px';
          fb.style.zIndex='200001';
          fb.style.width='44px';
          fb.style.height='44px';
          fb.style.border='none';
          fb.style.background='rgba(0,0,0,0.3)';
          fb.style.color='#fff';
          fb.style.borderRadius='8px';
          fb.style.display='inline-flex';
          fb.style.alignItems='center';
          fb.style.justifyContent='center';
          fb.addEventListener('click', function(e){ e.preventDefault(); toggle(); log('fallback toggle clicked'); });
          fb.addEventListener('touchstart', function(e){ e.preventDefault(); toggle(); log('fallback toggle touched'); }, {passive:false});
          document.body.appendChild(fb);
        }
      }
    }
    ensureFallback();

    // Try to attach again shortly in case elements are rendered later
    setTimeout(function(){
      // refresh toggles list and reattach
      const newToggles = Array.from(document.querySelectorAll('.mobile-sidebar-toggle, .sidebar-toggle, [data-toggle="sidebar"], button[onclick*="toggleSidebar"], a[onclick*="toggleSidebar"]'));
      if(newToggles.length && newToggles !== toggles){
        // replace toggles array (shallow) and attach
        while(toggles.length) toggles.pop();
        newToggles.forEach(t=>toggles.push(t));
        attachToToggles();
      }
      ensureFallback();
    }, 350);

    // Handle window resize - ensure desktop view shows sidebar and mobile hides overlay
    window.addEventListener('resize', function(){
      if(!sidebar) return;
      if(window.innerWidth >= 1024){
        // Desktop view - ensure sidebar is visible and overlay hidden
        sidebar.classList.remove('-translate-x-full');
        sidebar.classList.remove('open');
        if(overlay){ overlay.classList.add('hidden'); overlay.style.display='none'; overlay.style.pointerEvents='none'; }
      } else {
        // Mobile: keep previous open/closed state; nothing to do
      }
    });

    // expose a safe global toggle for any other inline handlers (keeps single source of truth)
    window.toggleSidebar = function(){ toggle(); };

    // quick visual aid during debugging: outline the sidebar when changed
    if(sidebar){
      const obs = new MutationObserver(()=>{ if(sidebar.classList.contains('open')){ sidebar.style.boxShadow='0 12px 40px rgba(0,0,0,0.6)'; } else { sidebar.style.boxShadow='2px 0 10px rgba(0,0,0,0.2)'; } });
      obs.observe(sidebar, { attributes:true, attributeFilter:['class'] });
    }
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', ensureHandlers);
  else ensureHandlers();

})();
