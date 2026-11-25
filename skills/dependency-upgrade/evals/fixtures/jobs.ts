import { createQueue, QueueOptions } from 'fastqueue';
import dayjs from 'dayjs';

const options: QueueOptions = { concurrency: 4, retry: { attempts: 3 } };

export const queue = createQueue(options);

queue.onFailed((job, err) => {
  console.error(`job ${job.id} failed at ${dayjs().toISOString()}`, err);
});

export function enqueueInvoice(id: string) {
  return queue.add('invoice', { id }, { delay: 1000 });
}
