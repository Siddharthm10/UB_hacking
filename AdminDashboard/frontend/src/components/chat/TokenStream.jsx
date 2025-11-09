import { MessageBubble } from './MessageBubble';
import { LoadingDots } from './LoadingDots';

export function TokenStream({ content, streaming }) {
  return (
    <div className="flex flex-col gap-2">
      <MessageBubble role="assistant" content={content || ''} streaming={streaming} />
      {streaming ? (
        <div className="flex justify-center">
          <LoadingDots />
        </div>
      ) : null}
    </div>
  );
}
