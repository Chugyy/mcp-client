import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Routes publiques (pas besoin d'authentification)
const publicRoutes = ['/login', '/forgot-password']

export function middleware(request: NextRequest) {
  // Vérifier la présence du cookie access_token
  const accessToken = request.cookies.get('access_token')

  const isPublicRoute = publicRoutes.some(route =>
    request.nextUrl.pathname.startsWith(route)
  )

  // Si pas de token et route protégée → rediriger vers /login
  if (!accessToken && !isPublicRoute) {
    const loginUrl = new URL('/login', request.url)
    return NextResponse.redirect(loginUrl)
  }

  // Si token présent et sur page login → rediriger vers /
  if (accessToken && request.nextUrl.pathname === '/login') {
    const homeUrl = new URL('/', request.url)
    return NextResponse.redirect(homeUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match toutes les routes sauf :
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
