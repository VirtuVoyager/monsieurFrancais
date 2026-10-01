"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap, type Schemas } from "./api/client";

export const keys = {
  path: ["path"] as const,
  module: (id: string) => ["module", id] as const,
  lesson: (id: string) => ["lesson", id] as const,
  due: ["reviews", "due"] as const,
  library: (kind: string, q: string) => ["library", kind, q] as const,
  budget: ["budget"] as const,
  budgetEvents: ["budget", "events"] as const,
};

export function usePath() {
  return useQuery({ queryKey: keys.path, queryFn: () => unwrap(api.GET("/path")) });
}

export function useModule(id: string) {
  return useQuery({
    queryKey: keys.module(id),
    queryFn: () => unwrap(api.GET("/modules/{module_id}", { params: { path: { module_id: id } } })),
  });
}

export function useLesson(id: string) {
  return useQuery({
    queryKey: keys.lesson(id),
    queryFn: () => unwrap(api.GET("/lessons/{lesson_id}", { params: { path: { lesson_id: id } } })),
  });
}

export function useCheckExercise(lessonId: string) {
  return useMutation({
    mutationFn: (body: Schemas["ExerciseAnswer"]) =>
      unwrap(
        api.POST("/lessons/{lesson_id}/check", {
          params: { path: { lesson_id: lessonId } },
          body,
        }),
      ),
  });
}

export function useCompleteLesson(lessonId: string, moduleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      unwrap(
        api.POST("/lessons/{lesson_id}/complete", { params: { path: { lesson_id: lessonId } } }),
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.path });
      void queryClient.invalidateQueries({ queryKey: keys.module(moduleId) });
      void queryClient.invalidateQueries({ queryKey: keys.lesson(lessonId) });
      void queryClient.invalidateQueries({ queryKey: keys.due });
    },
  });
}

export function useStartCheck(moduleId: string) {
  return useMutation({
    mutationFn: () =>
      unwrap(api.POST("/modules/{module_id}/check", { params: { path: { module_id: moduleId } } })),
  });
}

export function useSubmitCheck(moduleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, answers }: { runId: number; answers: Schemas["ItemAnswer"][] }) =>
      unwrap(
        api.POST("/checks/{run_id}", {
          params: { path: { run_id: runId } },
          body: { answers },
        }),
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.path });
      void queryClient.invalidateQueries({ queryKey: keys.module(moduleId) });
    },
  });
}

export function useDueReviews() {
  return useQuery({
    queryKey: keys.due,
    queryFn: () => unwrap(api.GET("/reviews/due", { params: { query: { limit: 50 } } })),
  });
}

export function useRateCard() {
  return useMutation({
    mutationFn: ({ id, rating }: { id: number; rating: number }) =>
      unwrap(
        api.POST("/reviews/{card_id}", { params: { path: { card_id: id } }, body: { rating } }),
      ),
  });
}

export function useLibraryWords(q: string) {
  return useQuery({
    queryKey: keys.library("words", q),
    queryFn: () => unwrap(api.GET("/library/words", { params: { query: { q: q || null } } })),
  });
}

export function useLibrarySentences(q: string) {
  return useQuery({
    queryKey: keys.library("sentences", q),
    queryFn: () => unwrap(api.GET("/library/sentences", { params: { query: { q: q || null } } })),
  });
}

export function useLibraryConcepts() {
  return useQuery({
    queryKey: keys.library("concepts", ""),
    queryFn: () => unwrap(api.GET("/library/concepts")),
  });
}

export function useBudget() {
  return useQuery({ queryKey: keys.budget, queryFn: () => unwrap(api.GET("/budget")) });
}

export function useBudgetEvents() {
  return useQuery({
    queryKey: keys.budgetEvents,
    queryFn: () => unwrap(api.GET("/budget/events", { params: { query: { limit: 50 } } })),
  });
}

export function useUpdateCaps() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (caps: Schemas["CapsUpdate"]) => unwrap(api.PUT("/budget/caps", { body: caps })),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: keys.budget }),
  });
}

export function useSkills() {
  return useQuery({ queryKey: ["skills"], queryFn: () => unwrap(api.GET("/skills")) });
}

export function useStartDrill() {
  return useMutation({
    mutationFn: (body: Schemas["DrillStart"]) => unwrap(api.POST("/drills", { body })),
  });
}

export function useSubmitDrill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, answers }: { runId: number; answers: Schemas["ItemAnswer"][] }) =>
      unwrap(
        api.POST("/drills/{run_id}", { params: { path: { run_id: runId } }, body: { answers } }),
      ),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["skills"] }),
  });
}

export function useSpeakingTasks() {
  return useQuery({
    queryKey: ["speaking", "tasks"],
    queryFn: () => unwrap(api.GET("/speaking/tasks")),
    staleTime: Infinity,
  });
}

export function useStartSpeaking() {
  return useMutation({
    mutationFn: (body: Schemas["SpeakingStart"]) =>
      unwrap(api.POST("/speaking/sessions", { body })),
  });
}

export function useNotes() {
  return useQuery({ queryKey: ["notes"], queryFn: () => unwrap(api.GET("/notes")) });
}

export function useNote(id: number) {
  return useQuery({
    queryKey: ["notes", id],
    queryFn: () => unwrap(api.GET("/notes/{note_id}", { params: { path: { note_id: id } } })),
  });
}

export function useUploadNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["NoteUpload"]) => unwrap(api.POST("/notes", { body })),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["notes"] }),
  });
}

export function useReviewNote(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (items: Schemas["NoteDecision"][]) =>
      unwrap(
        api.POST("/notes/{note_id}/review", {
          params: { path: { note_id: id } },
          body: { items },
        }),
      ),
    onSuccess: (note) => {
      queryClient.setQueryData(["notes", id], note);
      void queryClient.invalidateQueries({ queryKey: ["notes"], exact: true });
      void queryClient.invalidateQueries({ queryKey: ["library"] });
      void queryClient.invalidateQueries({ queryKey: keys.due });
    },
  });
}

export function useSettings() {
  return useQuery({ queryKey: ["settings"], queryFn: () => unwrap(api.GET("/settings")) });
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["LearnerSettings"]) => unwrap(api.PUT("/settings", { body })),
    onSuccess: (data) => queryClient.setQueryData(["settings"], data),
  });
}

export function useErrorFingerprint() {
  return useQuery({ queryKey: ["errors"], queryFn: () => unwrap(api.GET("/errors")) });
}

export function useSubmitLessonWriting(lessonId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (text: string) =>
      unwrap(
        api.POST("/lessons/{lesson_id}/writing", {
          params: { path: { lesson_id: lessonId } },
          body: { text },
        }),
      ),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["errors"] }),
  });
}

export function useStartWritingDrill() {
  return useMutation({ mutationFn: () => unwrap(api.POST("/writing/drills")) });
}

export function useSubmitWritingDrill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, text }: { runId: number; text: string }) =>
      unwrap(
        api.POST("/writing/drills/{run_id}", {
          params: { path: { run_id: runId } },
          body: { text },
        }),
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["skills"] });
      void queryClient.invalidateQueries({ queryKey: ["errors"] });
    },
  });
}

export function useStartPlacement() {
  return useMutation({ mutationFn: () => unwrap(api.POST("/placement")) });
}

export function useSubmitPlacement() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ runId, answers }: { runId: number; answers: Schemas["ItemAnswer"][] }) =>
      unwrap(
        api.POST("/placement/{run_id}", { params: { path: { run_id: runId } }, body: { answers } }),
      ),
    onSuccess: () => void queryClient.invalidateQueries(),
  });
}

export function useSearch(q: string, scope: "learned" | "catalogue" | "mine") {
  return useQuery({
    queryKey: ["search", q, scope],
    queryFn: () => unwrap(api.GET("/search", { params: { query: { q, scope } } })),
    enabled: q.length > 1,
    placeholderData: (previous) => previous,
  });
}
