<script lang="ts">
    import { Button } from "$lib/components/ui/button";
</script>

<main class="mx-auto max-w-3xl p-6 space-y-4">
    <h1 class="text-2xl font-semibold">Frontend setup check</h1>
    <p class="text-muted-foreground">
        Tailwind + shadcn-svelte smoke test.
    </p>

    <Button>Shadcn Button</Button>

    <div class="rounded-lg border p-4">
        <p class="text-sm">If you can see styles, Tailwind is working.</p>
    </div>
</main>