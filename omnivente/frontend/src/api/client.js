// Client HTTP unique pour toute l'application.
// Le jeton JWT est conserve en memoire + localStorage par AuthContext.

const BASE_URL = import.meta.env.VITE_API_URL || ''

export const TOKEN_KEY = 'omnivente_token'

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* stockage indisponible : la session durera le temps de l'onglet */
  }
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function request(path, { method = 'GET', body, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (auth && token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(`${BASE_URL}/api${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (response.status === 204) return null

  const text = await response.text()
  const data = text ? JSON.parse(text) : null

  if (!response.ok) {
    const detail = data?.detail
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg).join(', ')
          : 'Une erreur est survenue. Reessayez.'
    throw new ApiError(message, response.status)
  }
  return data
}

export const api = {
  // Authentification
  register: (payload) => request('/auth/register', { method: 'POST', body: payload, auth: false }),
  login: (payload) => request('/auth/login', { method: 'POST', body: payload, auth: false }),
  me: () => request('/auth/me'),
  updateProfile: (payload) => request('/auth/me', { method: 'PATCH', body: payload }),

  // Produits
  listProducts: () => request('/products'),
  createProduct: (payload) => request('/products', { method: 'POST', body: payload }),
  updateProduct: (id, payload) => request(`/products/${id}`, { method: 'PATCH', body: payload }),
  deleteProduct: (id) => request(`/products/${id}`, { method: 'DELETE' }),

  // Commandes
  listOrders: () => request('/orders'),
  swimlanes: () => request('/orders/swimlanes'),
  stats: () => request('/orders/stats'),
  createOrder: (payload) => request('/orders', { method: 'POST', body: payload }),
  updateOrderStatus: (id, status) =>
    request(`/orders/${id}/status`, { method: 'PATCH', body: { status } }),

  // Messagerie
  listConversations: () => request('/conversations'),
  conversation: (customerId) => request(`/conversations/${customerId}`),
  sendMessage: (payload) => request('/messages', { method: 'POST', body: payload }),
  simulateIncoming: (payload) => request('/messages/incoming', { method: 'POST', body: payload }),

  // Clients et FAQ
  listCustomers: () => request('/customers'),
  listFaq: () => request('/faq'),
  createFaq: (payload) => request('/faq', { method: 'POST', body: payload }),
}

export default api
