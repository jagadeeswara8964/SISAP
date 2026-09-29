import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";

export default function NotFoundPage() {
  return (
    <Card>
      <CardContent>
        <EmptyState
          icon={<Compass className="h-8 w-8" />}
          title="Page not found"
          description="The page you are looking for does not exist in SISAP."
          action={
            <Link to="/">
              <Button>Return to dashboard</Button>
            </Link>
          }
        />
      </CardContent>
    </Card>
  );
}
