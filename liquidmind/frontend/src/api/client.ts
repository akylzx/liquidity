const BASE_URL = "/api";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

// Accounts
export const getAccounts = () => fetchApi<any>("/accounts");
export const getAccount = (id: string) => fetchApi<any>(`/accounts/${id}`);
export const getAccountHistory = (id: string, days = 30) =>
  fetchApi<any>(`/accounts/${id}/history?days=${days}`);

// Forecasts
export const getAccountForecast = (id: string) =>
  fetchApi<any>(`/forecasts/account/${id}`);
export const getAggregateForecast = () =>
  fetchApi<any>("/forecasts/aggregate");
export const getForecastAccuracy = () =>
  fetchApi<any>("/forecasts/accuracy");

// Rebalancing
export const getRecommendations = () =>
  fetchApi<any>("/rebalancing/recommendations");
export const approveRecommendation = (id: string) =>
  fetchApi<any>(`/rebalancing/approve/${id}`, { method: "POST" });
export const rejectRecommendation = (id: string) =>
  fetchApi<any>(`/rebalancing/reject/${id}`, { method: "POST" });
export const getSavingsMetrics = () =>
  fetchApi<any>("/rebalancing/savings");

// Alerts
export const getAlerts = (severity?: string) =>
  fetchApi<any>(`/alerts${severity ? `?severity=${severity}` : ""}`);
export const acknowledgeAlert = (id: string) =>
  fetchApi<any>(`/alerts/${id}/acknowledge`, { method: "POST" });

// Stress Testing
export const getStressScenarios = () =>
  fetchApi<any>("/stress/scenarios");
export const runStressTest = (scenarioId: string) =>
  fetchApi<any>(`/stress/run/${scenarioId}`, { method: "POST" });
