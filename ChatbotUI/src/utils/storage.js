const safeWindow = typeof window !== 'undefined' ? window : undefined;

const USER_DATA_KEYS = [
  'AuthToken',
  'UserEmail',
  'UserProfile',
  'University',
  'UniversityUnitId',
  'UniversityState',
  'Programname',
  'Programnameview',
  'universityview',
  'ProgramDegree',
  'SelectedProgram',
  'SelectedDegreeLevel',
  'selectedComponent',
  'EditingPlan',
  'EditingPlanActive',
  'LocalSavedPlans',
  'CompareQueue',
  'LastCollegeDetail',
];

export const load = (key, fallback = null) => {
  if (!safeWindow) return fallback;
  try {
    const value = safeWindow.localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
};

export const save = (key, value) => {
  if (!safeWindow) return;
  try {
    safeWindow.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage is best-effort; callers retain their in-memory state.
  }
};

export const loadSession = (key, fallback = null) => {
  if (!safeWindow) return fallback;
  try {
    const value = safeWindow.sessionStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
};

export const saveSession = (key, value) => {
  if (!safeWindow) return;
  try {
    safeWindow.sessionStorage.setItem(key, JSON.stringify(value));
    safeWindow.localStorage.removeItem(key);
  } catch {
    // Storage is best-effort; callers retain their in-memory state.
  }
};

export const removeSession = (key) => {
  if (!safeWindow) return;
  try {
    safeWindow.sessionStorage.removeItem(key);
  } catch {
    // Storage cleanup is best-effort.
  }
};

export const remove = (key) => {
  if (!safeWindow) return;
  try {
    safeWindow.localStorage.removeItem(key);
  } catch {
    // Storage cleanup is best-effort.
  }
};

export const clearUserData = () => {
  if (!safeWindow) return;
  USER_DATA_KEYS.forEach((key) => {
    remove(key);
    try {
      safeWindow.sessionStorage?.removeItem(key);
    } catch {
      // Storage cleanup is best-effort.
    }
  });
};
