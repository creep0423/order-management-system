import type { ReactNode } from 'react'

interface InfoCardProps {
  title: string
  children: ReactNode
}

export function InfoCard({ title, children }: InfoCardProps) {
  return (
    <section className="info-card">
      <h2>{title}</h2>
      {children}
    </section>
  )
}
