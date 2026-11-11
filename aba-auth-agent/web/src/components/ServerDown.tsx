import { ServerCrash } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

/** Shown instead of the app (or the login form) when the server can't be asked who is signed in. */
export function ServerDown({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex min-h-svh items-center justify-center bg-muted/40 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <ServerCrash className="mb-2 size-8 text-muted-foreground" aria-hidden />
          <CardTitle>Can't reach Lumen ABA</CardTitle>
          <CardDescription>{message}</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={onRetry}>Try again</Button>
        </CardContent>
      </Card>
    </div>
  )
}
