package com.demo;

import com.demo.TextUtil;
import org.junit.Assert;
import org.junit.Test;

public class TextUtil_reverse_Str_Test_Boundary_46 {


    @Test
    public void testReverseWithNullString() {
        String input = null;
        String result = TextUtil.reverse(input);
        Assert.assertNull(result);
    }

}
