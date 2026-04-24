import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'https://prism-60b21aab4083.herokuapp.com/api/v1',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});
