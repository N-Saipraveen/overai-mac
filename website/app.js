"use strict";
const $ = (s) => document.querySelector(s);
const providers = [
  {
    id: "chatgpt",
    name: "ChatGPT",
    title: "A fresh perspective?",
    sub: "A little help for your next big idea.",
  },
  {
    id: "claude",
    name: "Claude",
    title: "Find your next good sentence.",
    sub: "A thoughtful space to shape your ideas.",
  },
  {
    id: "gemini",
    name: "Gemini",
    title: "Follow that spark.",
    sub: "Explore a different angle on your idea.",
  },
  {
    id: "grok",
    name: "Grok",
    title: "A different way to look at it.",
    sub: "Make a little room for curiosity.",
  },
  {
    id: "arena",
    name: "Arena",
    title: "Straight to the conversation.",
    sub: "Your AI conversation, in direct mode.",
  },
  {
    id: "muse",
    name: "Muse",
    title: "A place for your inspiration.",
    sub: "Another website. The same little window.",
  },
];
const reduce = matchMedia("(prefers-reduced-motion: reduce)");
let motionPaused = reduce.matches;
let demoTimer = null;
let demoPlaying = false;
let scene = 0;
let windowShown = true;
let opacity = 1;
function fade(element) {
  if (!motionPaused && !reduce.matches)
    element.animate(
      [
        { opacity: 0.25, transform: "translateY(5px)" },
        { opacity: 1, transform: "translateY(0)" },
      ],
      { duration: 350, easing: "ease-out" },
    );
}
function selectProvider(provider) {
  $("#active-icon").src = $("#chat-logo").src = `assets/${provider.id}.png`;
  $("#active-provider").textContent = provider.name;
  $("#chat-title").textContent = provider.title;
  $("#chat-subtitle").textContent = provider.sub;
  $("#provider-menu").hidden = true;
  $("#provider-toggle").setAttribute("aria-expanded", "false");
  const isMuse = provider.id === "muse";
  $("#example-question").textContent = isMuse
    ? "Your Muse website opens here."
    : "Help me turn this idea into a plan.";
  $("#example-answer strong").textContent = isMuse
    ? "A place for your videos."
    : "Start small. Make it real.";
  $("#example-answer p").textContent = isMuse
    ? "Browse and manage your video library. Website features depend on the service."
    : "Define the goal. Find the first step. Build something you’d love to use.";
  $(".chat-input").hidden = isMuse;
  fade($(".chat-content"));
}
providers.forEach((p) => {
  const createButton = () => {
    const b = document.createElement("button");
    const img = document.createElement("img");
    img.src = `assets/${p.id}.png`;
    img.alt = "";
    img.width = img.height = 23;
    const label = document.createElement("span");
    label.textContent = p.name;
    b.append(img, label);
    b.setAttribute("aria-label", `Preview ${p.name}`);
    b.addEventListener("click", () => {
      selectProvider(p);
      stopDemo();
      showWindow(true);
    });
    return b;
  };
  $("#provider-menu").append(createButton());
  $("#provider-strip-icons").append(createButton());
});
$("#provider-toggle").addEventListener("click", () => {
  stopDemo();
  const menu = $("#provider-menu");
  menu.hidden = !menu.hidden;
  $("#provider-toggle").setAttribute("aria-expanded", String(!menu.hidden));
  if (!menu.hidden) menu.querySelector("button").focus();
});
document.addEventListener("click", (e) => {
  if (!e.target.closest(".provider-menu,.provider-toggle")) {
    $("#provider-menu").hidden = true;
    $("#provider-toggle").setAttribute("aria-expanded", "false");
  }
});
$("#provider-menu").addEventListener("keydown", (e) => {
  const buttons = [...$("#provider-menu").querySelectorAll("button")];
  const i = buttons.indexOf(document.activeElement);
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    buttons[
      (i + (e.key === "ArrowDown" ? 1 : -1) + buttons.length) % buttons.length
    ].focus();
  }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("#provider-menu").hidden) {
    $("#provider-menu").hidden = true;
    $("#provider-toggle").setAttribute("aria-expanded", "false");
    $("#provider-toggle").focus();
  }
});
function showWindow(show) {
  windowShown = show;
  $("#ai-window").classList.toggle("dismissed", !show);
  $("#ai-window").inert = !show;
  $("#shortcut-demo").setAttribute("aria-pressed", String(show));
  $("#shortcut-demo>span").textContent = show
    ? "Your AI. Right here."
    : "Press to bring it back.";
}
$("#shortcut-demo").addEventListener("click", () => {
  stopDemo();
  showWindow(!windowShown);
});
function changeOpacity(delta) {
  opacity = Math.max(0.45, Math.min(1, opacity + delta));
  $("#ai-window").style.opacity = opacity;
  $("#opacity-down").disabled = opacity <= 0.45;
  $("#opacity-up").disabled = opacity >= 1;
}
$("#opacity-down").addEventListener("click", () => changeOpacity(-0.1));
$("#opacity-up").addEventListener("click", () => changeOpacity(0.1));
changeOpacity(0);
function stopDemo() {
  clearTimeout(demoTimer);
  demoTimer = null;
  demoPlaying = false;
  $("#demo-play").textContent = "▶ Play the walkthrough";
  $("#demo-play").setAttribute("aria-pressed", "false");
}
function playScene() {
  if (!demoPlaying || document.hidden) return;
  const scenes = [
    () => {
      selectProvider(providers[0]);
      showWindow(false);
      $("#demo-counter").textContent = "01 / 03";
      $("#shortcut-demo>span").textContent =
        "01 · Call it up with your shortcut.";
    },
    () => {
      showWindow(true);
      $("#demo-counter").textContent = "02 / 03";
      $("#shortcut-demo>span").textContent =
        "02 · Ask without leaving your work.";
    },
    () => {
      selectProvider(providers[1]);
      $("#demo-counter").textContent = "03 / 03";
      $("#shortcut-demo>span").textContent = "03 · Find a fresh perspective.";
    },
  ];
  scenes[scene]();
  scene = (scene + 1) % scenes.length;
  demoTimer = setTimeout(playScene, 3500);
}
function startDemo() {
  stopDemo();
  showWindow(true);
  if (motionPaused || reduce.matches) {
    $("#demo-counter").textContent = "Interactive preview";
    return;
  }
  demoPlaying = true;
  scene = 0;
  $("#demo-play").textContent = "Ⅱ Pause walkthrough";
  $("#demo-play").setAttribute("aria-pressed", "true");
  playScene();
}
$("#demo-play").addEventListener("click", () =>
  demoPlaying ? stopDemo() : startDemo(),
);
$("#watch").addEventListener("click", () => {
  $("#demo").scrollIntoView({
    behavior: motionPaused || reduce.matches ? "instant" : "smooth",
    block: "center",
  });
  startDemo();
});
const demoObserver = new IntersectionObserver(
  (entries) => {
    if (!entries[0].isIntersecting) stopDemo();
  },
  { threshold: 0.15 },
);
demoObserver.observe($("#demo"));
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    stopDemo();
  }
});
$("#reorder").addEventListener("click", () => {
  const lineup = $("#lineup");
  const first = lineup.querySelector("div");
  lineup.insertBefore(first, lineup.querySelector("button"));
  [...lineup.children].filter((e) => e.tagName === "DIV").forEach(fade);
});
const useCases = {
  write: {
    icon: "Aa",
    title: "Find the words you meant.",
    copy: "Give a rough draft a clearer shape, find a friendlier tone, or turn a page of thoughts into a simple outline.",
    prompt: "“Make this sound a little more like me.”",
  },
  build: {
    icon: "{ }",
    title: "A second pair of eyes.",
    copy: "Work through a confusing error, talk through an approach, or ask for a simpler explanation while your project stays in view.",
    prompt: "“Walk me through why this isn’t working.”",
  },
  learn: {
    icon: "?",
    title: "Stay curious. Go a little deeper.",
    copy: "Unpack an unfamiliar concept, explore a new subject, or ask the follow-up question that makes everything click.",
    prompt: "“Explain it with an example I’ll remember.”",
  },
};
const tabs = [...document.querySelectorAll("[role=tab]")];
function selectTab(tab) {
  tabs.forEach((b) => {
    b.setAttribute("aria-selected", String(b === tab));
    b.tabIndex = b === tab ? 0 : -1;
  });
  const c = useCases[tab.dataset.use];
  $(".use-index").textContent = c.icon;
  $("#use-title").textContent = c.title;
  $("#use-copy").textContent = c.copy;
  $("#use-prompt").textContent = c.prompt;
  $("#use-panel").setAttribute("aria-labelledby", tab.id);
  fade($("#use-panel"));
}
tabs.forEach((tab, i) => {
  tab.addEventListener("click", () => selectTab(tab));
  tab.addEventListener("keydown", (e) => {
    let n;
    if (e.key === "ArrowRight") n = (i + 1) % tabs.length;
    if (e.key === "ArrowLeft") n = (i + tabs.length - 1) % tabs.length;
    if (e.key === "Home") n = 0;
    if (e.key === "End") n = tabs.length - 1;
    if (n !== undefined) {
      e.preventDefault();
      selectTab(tabs[n]);
      tabs[n].focus();
    }
  });
});
const observer = new IntersectionObserver(
  (entries) =>
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add("visible");
        observer.unobserve(e.target);
      }
    }),
  { threshold: 0.07 },
);
document.querySelectorAll(".reveal").forEach((e) => observer.observe(e));
function syncMotion() {
  document.body.classList.toggle(
    "motion-paused",
    motionPaused || reduce.matches,
  );
  document.body.classList.toggle(
    "motion-enabled",
    !motionPaused && !reduce.matches,
  );
  $("#motion-toggle").textContent = motionPaused
    ? "Enable animations"
    : "Pause animations";
  $("#motion-toggle").setAttribute("aria-pressed", String(motionPaused));
  if (motionPaused || reduce.matches) {
    stopDemo();
    showWindow(true);
  }
}
$("#motion-toggle").addEventListener("click", () => {
  motionPaused = !motionPaused;
  syncMotion();
});
reduce.addEventListener("change", () => {
  motionPaused = reduce.matches;
  syncMotion();
});
syncMotion();

$("#capture-toggle").addEventListener("click", () => {
  const recording =
    $("#capture-toggle").getAttribute("aria-pressed") !== "true";
  $("#capture-toggle").setAttribute("aria-pressed", String(recording));
  $("#capture-monitor").classList.toggle("recording-view", recording);
  $("#capture-label").textContent = recording
    ? "Example recording · illustration"
    : "Your display · illustration";
  $("#capture-result").textContent = recording
    ? "Your work stays. OverAI is excluded.*"
    : "Capture protection · built in";
  $("#capture-toggle").firstChild.textContent = recording
    ? "Back to your display "
    : "Preview the recording ";
});

// The product proposition, rendered with lightweight DOM/CSS instead of video.
const positions = [
  { x: 20, y: 25, mx: 17, my: 19 },
  { x: 50, y: 12, mx: 50, my: 7 },
  { x: 80, y: 25, mx: 83, my: 19 },
  { x: 20, y: 73, mx: 17, my: 79 },
  { x: 50, y: 86, mx: 50, my: 88 },
  { x: 80, y: 73, mx: 83, my: 79 },
];
providers.forEach((provider, index) => {
  const create = (className) => {
    const button = document.createElement("button");
    button.className = className;
    const icon = document.createElement("img");
    icon.src = `assets/${provider.id}.png`;
    icon.alt = "";
    icon.width = 27;
    icon.height = 27;
    const name = document.createElement("span");
    name.textContent = provider.name;
    button.append(icon, name);
    button.setAttribute(
      "aria-label",
      `Choose ${provider.name} in the illustration`,
    );
    button.addEventListener("click", () => {
      selectProvider(provider);
      showWindow(true);
      stopDemo();
      document
        .querySelectorAll(".orbit-node")
        .forEach((b) =>
          b.setAttribute(
            "aria-pressed",
            String(b.dataset.provider === provider.id),
          ),
        );
      $("#hub-hint").textContent =
        `${provider.name}, in the same little window.`;
      $("#hub-active-icon").src = `assets/${provider.id}.png`;
      $("#hub-active-name").firstChild.textContent = provider.name;
      if (className === "hub-picker-option") $("#hub-button").focus();
      setHubOpen(false);
      fade($("#hub-button"));
    });
    return button;
  };
  const orbit = create("orbit-node");
  orbit.dataset.provider = provider.id;
  orbit.setAttribute("aria-pressed", "false");
  const p = positions[index];
  Object.entries({
    "--x": p.x + "%",
    "--y": p.y + "%",
    "--mx": p.mx + "%",
    "--my": p.my + "%",
    "--delay": -index * 1.1 + "s",
  }).forEach(([k, v]) => orbit.style.setProperty(k, v));
  $("#orbit-providers").append(orbit);
  $("#hub-picker-options").classList.add("hub-picker-options");
  $("#hub-picker-options").append(create("hub-picker-option"));
});
function setHubOpen(open) {
  $("#ai-hub").classList.toggle("hub-open", open);
  $("#hub-picker").hidden = !open;
  $("#hub-button").setAttribute("aria-expanded", String(open));
  if (open) {
    fade($("#hub-picker"));
    $("#hub-picker-options button").focus();
  }
}
$("#hub-button").addEventListener("click", () =>
  setHubOpen($("#hub-picker").hidden),
);
$("#hub-picker").addEventListener("keydown", (e) => {
  const buttons = [...$("#hub-picker-options").querySelectorAll("button")];
  const index = buttons.indexOf(document.activeElement);
  let step;
  if (e.key === "ArrowRight" || e.key === "ArrowDown") step = 1;
  if (e.key === "ArrowLeft" || e.key === "ArrowUp") step = -1;
  if (step) {
    e.preventDefault();
    buttons[(index + step + buttons.length) % buttons.length].focus();
  }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !$("#hub-picker").hidden) {
    setHubOpen(false);
    $("#hub-button").focus();
  }
});
document.addEventListener("click", (e) => {
  if (!e.target.closest(".hub-center")) setHubOpen(false);
});
let hubInView = false;
function syncHubActivity() {
  $("#ai-hub").classList.toggle("hub-offscreen", !hubInView || document.hidden);
}
const hubObserver = new IntersectionObserver(
  (entries) => {
    hubInView = entries[0].isIntersecting;
    syncHubActivity();
  },
  { threshold: 0.1 },
);
hubObserver.observe($("#ai-hub"));
document.addEventListener("visibilitychange", syncHubActivity);
