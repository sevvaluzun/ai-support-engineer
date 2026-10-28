
let demoAccessKey = "";

export function setDemoAccessKey(key) {
  demoAccessKey = key.trim();
}

export function getDemoAccessKey() {
  return demoAccessKey;
}

export async function apiFetch(url, options = {}) {
  const headers = new Headers(options.headers || {});

  if (demoAccessKey) {
    headers.set("X-Demo-Key", demoAccessKey);
  }

  return fetch(url, {
    ...options,
    headers,
  });
}
