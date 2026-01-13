import { AppLayout } from '@/components/layouts/app-layout';

export default function DashboardPage() {
  return (
    <AppLayout>
      <div className="flex flex-col items-center justify-center h-full">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground mt-2">Page en construction</p>
      </div>
    </AppLayout>
  );
}
