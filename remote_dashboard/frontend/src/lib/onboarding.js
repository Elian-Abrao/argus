import { driver } from 'driver.js';
import 'driver.js/dist/driver.css';

const STORAGE_KEY = 'onboarding_completed_v1';

export function isOnboardingCompleted() {
  try { return localStorage.getItem(STORAGE_KEY) === 'true'; } catch { return false; }
}

export function markOnboardingCompleted() {
  try { localStorage.setItem(STORAGE_KEY, 'true'); } catch { /* noop */ }
}

export function resetOnboarding() {
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* noop */ }
}

function aiImg(src, alt = 'AI assistant') {
  return `<img src="/ai/${src}" alt="${alt}" class="onboarding-ai-img" />`;
}

const steps = [
  {
    popover: {
      title: 'Hi! I\'m your AI assistant 👋',
      description:
        aiImg('greeting.webp', 'AI assistant waving') +
        'I\'m the intelligent assistant for this monitoring panel. Let me show you the main areas ' +
        'so you feel right at home. Ready?',
    },
  },
  {
    element: '[data-tour="sidebar-nav"]',
    popover: {
      title: 'This is your menu',
      description:
        aiImg('apontando.webp', 'AI assistant pointing') +
        'From here you navigate everything: machines, robots, clients, runs and schedules. ' +
        'Each area has a different purpose — let me show you the main ones.',
      side: 'right',
      align: 'start',
    },
  },
  {
    element: '[data-tour="nav-dashboard"]',
    popover: {
      title: 'Overview — your home page',
      description:
        aiImg('dashboard.webp', 'AI assistant with dashboard') +
        'Here you see the day\'s summary at a glance: how many runs happened, which failed, ' +
        'volume charts by hour and a visual timeline of everything that ran. ' +
        'It\'s the best starting point to understand how operations are going.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="nav-automations"]',
    popover: {
      title: 'Robots — the full catalog',
      description:
        aiImg('robo.webp', 'AI assistant with robot') +
        'All registered robots are here, with name, team, which machines they run on and for which clients. ' +
        'You can click any one to see details and run history.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="nav-runs"]',
    popover: {
      title: 'Runs — the tracking center',
      description:
        aiImg('checklist.webp', 'AI assistant with checklist') +
        'The most powerful screen in the panel! Filter by client, machine, status or period. ' +
        'Click any run to investigate detailed logs, timeline, ' +
        'resource metrics and even emails the robot sent.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="nav-schedules"]',
    popover: {
      title: 'Schedules — control the timing',
      description:
        aiImg('calendario.webp', 'AI assistant with calendar') +
        'Create recurring schedules for your robots: daily, weekly, monthly, or only on business days. ' +
        'You can also trigger a run right now with "Run Now". ' +
        'The calendar shows everything that is scheduled.',
      side: 'right',
    },
  },
  {
    element: '[data-tour="header-user"]',
    popover: {
      title: 'Your profile',
      description:
        aiImg('cracha.webp', 'AI assistant with badge') +
        'Click your name to see your permissions, change your password ' +
        'and replay this tour whenever you want.',
      side: 'bottom',
      align: 'end',
    },
  },
  {
    element: '[data-tour="ai-button"]',
    popover: {
      title: 'And here I am! 💬',
      description:
        aiImg('sorrindo.webp', 'AI assistant smiling') +
        'I\'m your AI assistant. Ask me anything: ' +
        '"Which robots failed today?", "How is robot X doing?", ' +
        '"How many runs did we have this week?". ' +
        'I query the data in real time and answer right away.',
      side: 'left',
      align: 'end',
    },
  },
  {
    popover: {
      title: 'All set! 🎉',
      description:
        aiImg('success.webp', 'AI assistant celebrating') +
        'Now you know the panel. Explore freely and, if you have any questions, ' +
        'just call me with the purple button in the corner. I\'m always here!',
    },
  },
];

export function startOnboardingTour({ onComplete } = {}) {
  const driverObj = driver({
    showProgress: true,
    animate: true,
    allowHTMLDescription: true,
    overlayColor: 'rgba(15, 5, 30, 0.75)',
    stagePadding: 8,
    stageRadius: 12,
    popoverClass: 'onboarding-popover',
    nextBtnText: 'Next',
    prevBtnText: 'Previous',
    doneBtnText: 'Done',
    progressText: '{{current}} of {{total}}',
    steps,
    onDestroyStarted: () => {
      markOnboardingCompleted();
      driverObj.destroy();
      onComplete?.();
    },
  });

  driverObj.drive();
  return driverObj;
}
