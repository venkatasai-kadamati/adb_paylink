import type { NextConfig } from 'next';
const config: NextConfig = {
  async rewrites() { return [{ source: '/api/:path*', destination: `${process.env.BACKEND_URL || 'http://127.0.0.1:8000'}/api/:path*` }]; },
  async headers() { return [{source:'/:path*',headers:[{key:'X-Frame-Options',value:'DENY'},{key:'Referrer-Policy',value:'same-origin'},{key:'X-Content-Type-Options',value:'nosniff'}]}]; },
};
export default config;
