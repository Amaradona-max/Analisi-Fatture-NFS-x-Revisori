import axios from 'axios'

const DEV_HOSTNAME =
  typeof window !== 'undefined' && window.location?.hostname
    ? window.location.hostname
    : 'localhost'

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD
    ? 'https://nfs-ft-backend.onrender.com'
    : `http://${DEV_HOSTNAME}:8000`)

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
})

export const fileAPI = {
  processFile: async (file, onProgress) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await api.post('/api/process-file', formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          onProgress?.(percentCompleted)
        },
      })
      return response.data
    } catch (error) {
      throw new Error(
        error.response?.data?.detail || 'Errore durante il caricamento del file'
      )
    }
  },
  processFilePisa: async (file, onProgress) => {
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await api.post('/api/process-file-pisa', formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          onProgress?.(percentCompleted)
        },
      })
      return response.data
    } catch (error) {
      throw new Error(
        error.response?.data?.detail || 'Errore durante il caricamento del file'
      )
    }
  },
  processCompare: async (fileNfs, filePisa, onProgress) => {
    const formData = new FormData()
    formData.append('file_nfs', fileNfs)
    formData.append('file_pisa', filePisa)

    try {
      const response = await api.post('/api/process-compare', formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          onProgress?.(percentCompleted)
        },
      })
      return response.data
    } catch (error) {
      throw new Error(
        error.response?.data?.detail || 'Errore durante il caricamento del file'
      )
    }
  },

  downloadFile: async (fileId) => {
    try {
      const response = await api.get(`/api/download/${fileId}`, {
        responseType: 'blob',
      })
      return response.data
    } catch {
      throw new Error('Errore durante il download del file')
    }
  },

  healthCheck: async () => {
    const response = await api.get('/api/health')
    return response.data
  },
  closeDay: async (message) => {
    try {
      const response = await api.post(
        '/api/close-day',
        { message },
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      )
      return response.data
    } catch (error) {
      throw new Error(
        error.response?.data?.detail || 'Errore durante la chiusura della giornata'
      )
    }
  },
}

export default api
