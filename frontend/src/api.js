import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const client = axios.create({ baseURL: `${API_URL}/api` })

export async function fetchCompanies() {
  const { data } = await client.get('/companies')
  return data
}

export async function fetchResults(companyId) {
  const { data } = await client.get(`/results/${companyId}`)
  return data
}

export async function screenCompany(companyId) {
  const { data } = await client.post(`/screen/${companyId}`)
  return data
}
