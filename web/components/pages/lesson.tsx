"use client";

import { ArrowLeft, Check } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Glossed } from "@/components/glossary/glossed";
import { LessonView } from "@/components/lesson/lesson-view";
import { Button } from "@/components/ui/button";
import { Eyebrow } from "@/components/ui/card";
import { ErrorState, Loading } from "@/components/ui/states";
import { fr } from "@/lib/french";
import { useCompleteLesson, useLesson, useModule } from "@/lib/queries";

export function LessonPage({ id }: { id: string }) {
  const moduleId = id.split("/")[0];
  const lesson = useLesson(id);
  const moduleQuery = useModule(moduleId);
  const complete = useCompleteLesson(id, moduleId);
  const router = useRouter();

  if (lesson.isPending) return <Loading />;
  if (lesson.isError) return <ErrorState error={lesson.error} />;

  const lessons = moduleQuery.data?.lessons ?? [];
  const index = lessons.findIndex((l) => l.id === id);
  const next = index >= 0 ? lessons[index + 1] : undefined;

  const finish = async () => {
    if (!lesson.data.done) await complete.mutateAsync();
    router.push(next ? `/lessons/${next.id}` : `/modules/${moduleId}`);
  };

  return (
    <Glossed moduleId={moduleId}>
      <article className="space-y-6">
        <Link
          href={`/modules/${moduleId}`}
          className="inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
        >
          <ArrowLeft className="size-4" aria-hidden />{" "}
          {moduleQuery.data ? fr(moduleQuery.data.title) : "Module"}
        </Link>
        <header>
          <Eyebrow>
            Lesson {index + 1} of {lessons.length || "…"}
          </Eyebrow>
          <h1 className="mt-1 font-serif text-3xl font-semibold" lang="fr">
            {fr(lesson.data.title)}
          </h1>
        </header>

        <LessonView lesson={lesson.data} />

        <div className="flex items-center justify-end gap-3">
          {lesson.data.done && (
            <span className="inline-flex items-center gap-1 text-sm text-success">
              <Check className="size-4" aria-hidden /> Completed
            </span>
          )}
          <Button onClick={finish} disabled={complete.isPending}>
            {lesson.data.done ? (next ? "Next lesson" : "Back to module") : "Complete lesson"}
          </Button>
        </div>
      </article>
    </Glossed>
  );
}
