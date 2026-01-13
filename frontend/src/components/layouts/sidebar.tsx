"use client"

import { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import {
  Sidebar as SidebarPrimitive,
  SidebarContent
} from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import { NavMenu } from '@/components/navigation/nav-menu'
import { ConversationList } from '@/components/chat/conversation-list'

/**
 * Sidebar principale avec pattern SSR-safe pour éviter hydration mismatch
 * Utilise un skeleton pendant SSR puis monte les composants Radix en client-side uniquement
 */
export function Sidebar() {
  const [mounted, setMounted] = useState(false)
  const pathname = usePathname()

  useEffect(() => {
    setMounted(true)
  }, [])

  // SSR: skeleton simple sans composants Radix pour éviter mismatch d'IDs
  if (!mounted) {
    return (
      <div className="w-64 border-r bg-sidebar" />
    )
  }

  // CSR uniquement: Rendu complet avec tous les composants Radix
  return (
    <SidebarPrimitive collapsible="offcanvas">
      <SidebarContent className="flex flex-col">
        {/* Header */}
        <div className="px-6 py-5 flex items-center gap-3">
          <img
            src="/logo.svg"
            alt="Logo"
            width={24}
            height={24}
            className="shrink-0"
          />
          <h2 className="text-base font-bold">Multimodal AI Client</h2>
        </div>

        {/* Navigation principale */}
        <NavMenu />

        <Separator className="my-2" />

        {/* Liste des conversations */}
        <ConversationList />
      </SidebarContent>
    </SidebarPrimitive>
  )
}
