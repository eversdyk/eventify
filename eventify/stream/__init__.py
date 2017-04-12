"""
Handle Stream Related Functions
"""
import json
import time

import beanstalkt
import tornado.gen

from eventify import Eventify, logger
from eventify.persist import persist_event

class Stream(Eventify):
    """
    The stream object
    """

    def __init__(self, host='localhost', topic='default', driver='beanstalkd', **kwargs):
        """
        Constructor method

        Args:
            host (str): Hostname
            topic (str): Topic Name
            driver (str): Name of driver the service wants to use
        """
        self.host = host
        self.topic = topic
        self.driver = driver
        logger.debug('configured steam: %s %s' % (host, topic))

        if driver == 'beanstalkd':
            self.client = beanstalkt.Client(host=self.host)
            self.connect()
            logger.debug(self.client.stats())
            logger.debug('connected to stream!')

        super(Stream, self).__init__(**kwargs)


    @tornado.gen.coroutine
    def connect(self):
        """
        Connect to stream
        """
        yield self.client.connect()
        yield self.client.use(self.topic)


    @tornado.gen.coroutine
    def listen(self, callback, timeout=0, react_in=0):
        """
        Start listening to a stream

        Args:
            timeout (int): Seconds to prevent other workers from reading event
        """
        if self.driver == 'beanstalkd':
            yield self.client.watch(self.topic)

            while True:
                event = yield self.client.reserve(timeout=timeout)
                try:
                    if 'id' in event:
                        if react_in != 0:
                            time.sleep(react_in)
                        event_id = event['id']
                        message = json.loads(event['body'].decode())
                        callback(event_id, message)
                except TypeError:
                    pass
        else:
            raise ValueError("Stream driver not supported: %s" % self.driver)


    @tornado.gen.coroutine
    def emit_event(self, event, persist=True):
        """
        Emit event to stream

        Args:
            event (dict): Dictionary
            persist (bool): Persist to persistant store
        """
        if self.driver == 'beanstalkd':
            if persist:
                # Write to persistant store
                persist_event(event)
                logger.debug('event persisted to db!')

            # Convert string to bytes
            payload = str.encode(json.dumps(event))
            logger.debug(payload)
            yield self.client.put(payload)
            logger.debug('event published!')


    @tornado.gen.coroutine
    def delete_event(self, event_id):
        """
        Delete event from stream

        Args:
            event_id (int): ID of event
        """
        if self.driver == 'beanstalkd':
            yield self.client.delete(event_id)
