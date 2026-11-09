export default function Page() {
  const act = async (fd: FormData) => {
    "use server";
    // ruleid: nextjs-ssrf
    await fetch(String(fd.get("u")));
  };
  const notAction = async (value: string) => {
    // ok: nextjs-ssrf
    await fetch(value);
  };
  return <form action={act} onSubmit={() => notAction("x")} />;
}
