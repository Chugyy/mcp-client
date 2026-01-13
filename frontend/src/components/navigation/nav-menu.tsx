"use client"

import { useState, useId } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton
} from '@/components/ui/sidebar'
import {
  ChevronDown,
  CheckCircle,
  Zap,
  Bot,
  Package,
  BookOpen
} from 'lucide-react'

interface NavSection {
  title: string
  items: NavItem[]
}

interface NavItem {
  href: string
  label: string
  icon: React.ComponentType<{ className?: string }>
}

const navSections: NavSection[] = [
  {
    title: 'Navigation',
    items: [
      { href: '/validation', label: 'Validation', icon: CheckCircle },
      { href: '/automatisations', label: 'Automatisations', icon: Zap },
    ]
  },
  {
    title: 'Construction',
    items: [
      { href: '/agents', label: 'Agents', icon: Bot },
      { href: '/mcp-tools', label: 'MCP et outils', icon: Package },
      { href: '/ressources', label: 'Ressources', icon: BookOpen },
    ]
  }
]

export function NavMenu() {
  const pathname = usePathname()
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    'Navigation': true,
    'Construction': true
  })

  const toggleSection = (title: string) => {
    setOpenSections(prev => ({
      ...prev,
      [title]: !prev[title]
    }))
  }

  return (
    <>
      {navSections.map((section) => (
        <Collapsible
          key={section.title}
          open={openSections[section.title]}
          onOpenChange={() => toggleSection(section.title)}
        >
          <SidebarGroup className="flex-shrink-0">
            <CollapsibleTrigger asChild>
              <SidebarGroupLabel className="cursor-pointer hover:bg-sidebar-accent hover:text-sidebar-accent-foreground rounded-md flex items-center justify-between">
                <span>{section.title}</span>
                <ChevronDown
                  className={`size-4 transition-transform ${
                    openSections[section.title] ? '' : '-rotate-90'
                  }`}
                />
              </SidebarGroupLabel>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <SidebarGroupContent>
                <SidebarMenu>
                  {section.items.map((item) => (
                    <SidebarMenuItem key={item.href}>
                      <Link href={item.href}>
                        <SidebarMenuButton isActive={pathname === item.href}>
                          <item.icon className="size-4" />
                          <span>{item.label}</span>
                        </SidebarMenuButton>
                      </Link>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </CollapsibleContent>
          </SidebarGroup>
        </Collapsible>
      ))}
    </>
  )
}
