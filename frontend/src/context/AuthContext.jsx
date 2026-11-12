import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { AuthContext } from './authContext.js'
import api, { AUTH_TOKEN_KEY } from '../services/api.js'

function decodeJwtPayload(token) {
  try {
    const encodedPayload = token.split('.')[1]
    if (!encodedPayload) return null

    const base64 = encodedPayload.replace(/-/g, '+').replace(/_/g, '/')
    const paddedBase64 = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=')
    const bytes = Uint8Array.from(atob(paddedBase64), (character) =>
      character.charCodeAt(0),
    )
    return JSON.parse(new TextDecoder().decode(bytes))
  } catch {
    return null
  }
}

function normalizeRole(role) {
  return typeof role === 'string' ? role.toUpperCase() : undefined
}

function userFromToken(token) {
  const payload = decodeJwtPayload(token)
  const role = normalizeRole(payload?.role)
  return role ? { role } : null
}

export function AuthProvider({ children }) {
  const queryClient = useQueryClient()
  const [token, setToken] = useState(() => localStorage.getItem(AUTH_TOKEN_KEY))
  const [user, setUser] = useState(() => {
    const savedToken = localStorage.getItem(AUTH_TOKEN_KEY)
    return savedToken ? userFromToken(savedToken) : null
  })
  const [loading, setLoading] = useState(Boolean(token))

  const clearSession = useCallback(() => {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    setToken(null)
    setUser(null)
    setLoading(false)
    queryClient.clear()
  }, [queryClient])

  const loadCurrentUser = useCallback(async (accessToken) => {
    const response = await api.get('/auth/me', {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    const currentUser = {
      ...response.data,
      role: normalizeRole(response.data.role),
    }
    setUser(currentUser)
    return currentUser
  }, [])

  useEffect(() => {
    if (!token) {
      return
    }

    let active = true
    // Loading the session requires applying the server's current user response.
    // oxlint-disable-next-line react/set-state-in-effect
    loadCurrentUser(token)
      .catch(() => {
        if (active) clearSession()
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [clearSession, loadCurrentUser, token])

  const login = useCallback(
    async (credentials) => {
      const response = await api.post('/auth/login', credentials)
      const accessToken = response.data.access_token
      localStorage.setItem(AUTH_TOKEN_KEY, accessToken)
      setToken(accessToken)
      try {
        return await loadCurrentUser(accessToken)
      } catch (error) {
        clearSession()
        throw error
      }
    },
    [clearSession, loadCurrentUser],
  )

  const logout = useCallback(() => {
    clearSession()
  }, [clearSession])

  useEffect(() => {
    window.addEventListener('auth:unauthorized', clearSession)
    return () => window.removeEventListener('auth:unauthorized', clearSession)
  }, [clearSession])

  const value = useMemo(
    () => ({ token, user, loading, login, logout }),
    [token, user, loading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
